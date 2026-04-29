"""
bot.py
Telegram bot for reviewing Greek flashcards from Kindle highlights.
"""

import asyncio
import io
import logging
import os
from telegram import BotCommand, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

import config
from clippings_parser import parse_clippings, discover_books, set_book_epub
from epub_reader import load_epub_text, find_context
from card_generator import generate_card
from state import StateManager, Card

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_EDIT = 1

state_manager = StateManager(config.STATE_FILE)

# Per-book epub text cache: book_id -> full text string
epub_cache: dict[str, str] = {}

_prefetch_task: asyncio.Task | None = None


def _reload_books():
    """Re-read books.json into config.BOOKS after an update."""
    import json as _json
    with open(config.BOOKS_FILE, encoding="utf-8") as f:
        raw = _json.load(f)
    config.BOOKS = {
        book_id: {**book, "epub": os.path.expanduser(book["epub"]) if book.get("epub") else ""}
        for book_id, book in raw.items()
    }


def get_epub_text(book_id: str) -> str | None:
    if book_id not in epub_cache:
        book_info = config.BOOKS.get(book_id)
        if not book_info or not book_info.get("epub"):
            logger.warning(f"No epub configured for book {book_id}")
            return None
        logger.info(f"Loading epub for {book_info['title']}...")
        epub_cache[book_id] = load_epub_text(book_info["epub"])
        logger.info(f"Loaded {len(epub_cache[book_id])} chars")
    return epub_cache[book_id]


def get_new_highlights() -> list:
    """Get unprocessed highlights for books that have an epub configured."""
    books_with_epub = {
        book_id for book_id, info in config.BOOKS.items() if info.get("epub")
    }
    all_highlights = parse_clippings(config.CLIPPINGS_PATH)
    new = [
        h for h in all_highlights
        if not state_manager.is_processed(h.annotation_id) and h.book_id in books_with_epub
    ]
    logger.debug(
        "get_new_highlights: %d total, %d with epub, %d unprocessed, %d processed_ids",
        len(all_highlights), len(books_with_epub), len(new), len(state_manager.state.processed_ids),
    )
    return new


async def maybe_auto_export(update: Update):
    """Send CSV to Telegram and clear accepted queue when threshold is reached."""
    if len(state_manager.state.accepted_cards) < config.AUTO_EXPORT_THRESHOLD:
        return
    cards = state_manager.pop_accepted_cards()
    buf = io.StringIO()
    for card in cards:
        back = f"{card.back} | {card.note}" if card.note else card.back
        buf.write(f"{card.front}\t{back}\n")
    buf.seek(0)
    await update.effective_message.reply_document(
        document=io.BytesIO(buf.read().encode("utf-8")),
        filename="greek_flashcards.txt",
        caption=f"🎉 {len(cards)} cards ready! Import into Quizlet: Create set → Import → Tab between term/definition, New line between cards.",
    )


def format_card_message(card: Card) -> str:
    book_title = config.BOOKS.get(card.asin, {}).get("title", card.asin)
    return (
        f"📖 *{escape_md(card.highlight)}*  _\\({escape_md(book_title)}\\)_\n\n"
        f"Context:\n_{escape_md(card.context)}_\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"*Proposed card:*\n"
        f"🇬🇷 Front: *{escape_md(card.front)}*\n"
        f"🇷🇺 Back: *{escape_md(card.back)}*\n"
        f"💡 Note: _{escape_md(card.note)}_"
    )


def escape_md(text: str) -> str:
    """Escape MarkdownV2 special chars."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


async def _prefetch_next_card():
    new_highlights = get_new_highlights()
    if not new_highlights:
        return
    highlight = new_highlights[0]
    if any(c.annotation_id == highlight.annotation_id for c in state_manager.state.pending_cards):
        return  # already queued from a prior prefetch
    epub_text = get_epub_text(highlight.book_id)
    if epub_text is not None:
        data = find_context(epub_text, highlight.text)
        if data is None:
            data = {"highlight": highlight.text, "context": highlight.text}
    else:
        data = {"highlight": highlight.text, "context": highlight.text}
    book_title = config.BOOKS.get(highlight.book_id, {}).get("title", highlight.book_title)
    logger.debug("Prefetching card for '%s' (%s)", highlight.text[:40], book_title)
    try:
        card_data = await asyncio.to_thread(
            generate_card, data["highlight"], data["context"], config.ANTHROPIC_API_KEY
        )
    except Exception as e:
        logger.warning("Prefetch failed: %s", e)
        return
    card = Card(
        annotation_id=highlight.annotation_id,
        asin=highlight.book_id,
        highlight=data["highlight"],
        context=data["context"],
        front=card_data.get("front", data["highlight"]),
        back=card_data.get("back", ""),
        note=card_data.get("note", ""),
    )
    state_manager.add_pending(card)
    state_manager.mark_processed(highlight.annotation_id)
    logger.debug("Prefetch done: %s → %s", card.front, card.back)


def _schedule_prefetch():
    global _prefetch_task
    if _prefetch_task and not _prefetch_task.done():
        return
    _prefetch_task = asyncio.create_task(_prefetch_next_card())


def card_keyboard(annotation_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"accept:{annotation_id}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit:{annotation_id}"),
            InlineKeyboardButton("⏭ Skip", callback_data=f"skip:{annotation_id}"),
        ]
    ])


async def process_next_highlight(update: Update, context: ContextTypes.DEFAULT_TYPE, silent=False):
    """Show next pending card if any, otherwise fetch and process a new highlight."""
    pending = state_manager.state.pending_cards
    if pending:
        card = pending[0]
        await update.effective_message.reply_text(
            format_card_message(card),
            parse_mode="MarkdownV2",
            reply_markup=card_keyboard(card.annotation_id),
        )
        _schedule_prefetch()
        return card

    new_highlights = get_new_highlights()

    if not new_highlights:
        if not silent:
            await update.effective_message.reply_text("🎉 All highlights processed! Use /export to get your cards.")
        return None

    highlight = new_highlights[0]
    logger.debug(f"Processing highlight {highlight.annotation_id} from book {highlight.book_id} loc {highlight.location_start}")
    epub_text = get_epub_text(highlight.book_id)
    if epub_text is not None:
        data = find_context(epub_text, highlight.text)
        if data is None:
            logger.warning(f"Could not find '{highlight.text}' in epub, using highlight text only")
            data = {"highlight": highlight.text, "context": highlight.text}
    else:
        data = {"highlight": highlight.text, "context": highlight.text}

    book_title = config.BOOKS.get(highlight.book_id, {}).get("title", highlight.book_title)
    await update.effective_message.reply_text(f"⏳ Generating card with Claude... _{book_title}_", parse_mode="Markdown")

    try:
        card_data = generate_card(data["highlight"], data["context"], config.ANTHROPIC_API_KEY)
    except Exception as e:
        state_manager.mark_processed(highlight.annotation_id)
        await update.effective_message.reply_text(
            f"⚠️ Skipped *{escape_md(highlight.text)}* — Claude didn't return a valid card\\.\n"
            f"_{escape_md(str(e))}_",
            parse_mode="MarkdownV2",
        )
        return None

    card = Card(
        annotation_id=highlight.annotation_id,
        asin=highlight.book_id,
        highlight=data["highlight"],
        context=data["context"],
        front=card_data.get("front", data["highlight"]),
        back=card_data.get("back", ""),
        note=card_data.get("note", ""),
    )
    state_manager.add_pending(card)
    state_manager.mark_processed(highlight.annotation_id)

    await update.effective_message.reply_text(
        format_card_message(card),
        parse_mode="MarkdownV2",
        reply_markup=card_keyboard(card.annotation_id),
    )
    _schedule_prefetch()
    return card


async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_next_highlight(update, context)



async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new = get_new_highlights()
    s = state_manager.state

    # Per-book remaining
    from collections import Counter
    remaining_by_book = Counter(h.book_id for h in new)
    book_lines = ""
    for book_id, count in remaining_by_book.items():
        title = config.BOOKS.get(book_id, {}).get("title", book_id)
        book_lines += f"  • {title}: {count}\n"

    msg = (
        f"📊 *Stats*\n\n"
        f"✅ Accepted: {len(s.accepted_cards)}\n"
        f"⏳ Pending review: {len(s.pending_cards)}\n"
        f"📚 Remaining highlights: {len(new)}\n"
        + (f"\n*By book:*\n{book_lines}" if book_lines else "")
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = state_manager.state.pending_cards
    if not cards:
        await update.message.reply_text("No pending cards.")
        return
    for card in cards[-5:]:  # show last 5
        await update.message.reply_text(
            format_card_message(card),
            parse_mode="MarkdownV2",
            reply_markup=card_keyboard(card.annotation_id),
        )


# --- Callback handlers ---

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, annotation_id = query.data.split(":", 1)

    if action == "accept":
        card = state_manager.accept_card(annotation_id)
        if card:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"✅ Accepted: *{card.front}* → {card.back}", parse_mode="Markdown")
            await maybe_auto_export(update)
            await process_next_highlight(update, context)

    elif action == "skip":
        state_manager.skip_card(annotation_id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("⏭ Skipped.")
        await process_next_highlight(update, context)

    elif action == "setepub":
        book_id = annotation_id
        title = config.BOOKS.get(book_id, {}).get("title", book_id)
        context.user_data["pending_epub_book_id"] = book_id
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"Send the epub file for *{escape_md(title)}*\\.", parse_mode="MarkdownV2")

    elif action == "edit":
        for card in state_manager.state.pending_cards:
            if card.annotation_id == annotation_id:
                context.user_data["editing_id"] = annotation_id
                await query.message.reply_text(
                    f"✏️ Edit the card for *{card.highlight}*\n\n"
                    "Send your correction in this format:\n"
                    "`front | back | note`\n\n"
                    "Example: `πηδώ | to jump | verb, 1st person present`",
                    parse_mode="Markdown"
                )
                return


async def handle_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    annotation_id = context.user_data.get("editing_id")
    if not annotation_id:
        return

    text = update.message.text.strip()
    parts = [p.strip() for p in text.split("|")]

    if len(parts) < 2:
        await update.message.reply_text("Please use format: `front | back | note`", parse_mode="Markdown")
        return

    front = parts[0] if len(parts) > 0 else None
    back = parts[1] if len(parts) > 1 else None
    note = parts[2] if len(parts) > 2 else None

    card = state_manager.accept_card(annotation_id, front=front, back=back, note=note)
    context.user_data.pop("editing_id", None)

    if card:
        await update.message.reply_text(
            f"✅ Saved: *{card.front}* → {card.back}",
            parse_mode="Markdown"
        )
        await maybe_auto_export(update)
        await process_next_highlight(update, context)
    else:
        await update.message.reply_text("Card not found, may have already been processed.")


async def cmd_setepub(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    new_books = discover_books(config.CLIPPINGS_PATH, config.BOOKS_FILE)
    if new_books:
        logger.info("Discovered %d new book(s): %s", len(new_books), new_books)
        _reload_books()
    books = config.BOOKS
    if not books:
        await update.message.reply_text("No books discovered yet. Sync your clippings first.")
        return
    keyboard = [
        [InlineKeyboardButton(info["title"], callback_data=f"setepub:{book_id}")]
        for book_id, info in books.items()
    ]
    await update.message.reply_text("Which book?", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        return

    book_id = context.user_data.get("pending_epub_book_id")
    if doc.file_name and doc.file_name.endswith(".epub") and book_id:
        epub_path = os.path.join(config.EPUBS_DIR, f"{book_id}.epub")
        file = await doc.get_file()
        await file.download_to_drive(epub_path)
        set_book_epub(config.BOOKS_FILE, book_id, epub_path)
        _reload_books()
        epub_cache.pop(book_id, None)
        context.user_data.pop("pending_epub_book_id", None)
        title = config.BOOKS.get(book_id, {}).get("title", book_id)
        logger.info(f"Epub saved for {book_id} at {epub_path}")
        await update.message.reply_text(f"✅ Epub saved for *{title}*.", parse_mode="Markdown")


async def cmd_unknown(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    lines = "\n".join(f"/{name} — {desc}" for name, _, desc in COMMANDS)
    await update.message.reply_text(f"Unknown command. Available:\n{lines}")


COMMANDS = [
    ("next",    cmd_next,    "Review next card or generate from a new highlight"),
    ("stats",   cmd_stats,   "Show progress per book"),
    ("pending", cmd_pending, "Re-show last 5 unreviewed cards"),
    ("setepub", cmd_setepub, "Upload an epub for a book"),
]


async def post_init(app: Application):
    await app.bot.set_my_commands(
        [BotCommand(name, desc) for name, _, desc in COMMANDS]
    )
    logger.info("Bot commands registered with Telegram.")


def main():
    new_books = discover_books(config.CLIPPINGS_PATH, config.BOOKS_FILE)
    if new_books:
        logger.info("Discovered %d new book(s): %s", len(new_books), new_books)
        _reload_books()

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    for name, handler, _ in COMMANDS:
        app.add_handler(CommandHandler(name, handler))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_message))
    app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    logger.info("Bot started. Listening...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
