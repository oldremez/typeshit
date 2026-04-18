"""
bot.py
Telegram bot for reviewing Greek flashcards from Kindle highlights.

Commands:
  /next    — process next unprocessed highlight
  /batch N — process N highlights at once (default 5)
  /export  — export accepted cards to CSV
  /stats   — show progress stats
  /pending — show how many cards are waiting for review
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

import config
from clippings_parser import parse_clippings
from epub_reader import load_epub_text, find_context
from card_generator import generate_card
from state import StateManager, Card
from exporter import export_to_csv

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_EDIT = 1

state_manager = StateManager(config.STATE_FILE)

# Per-book epub text cache: asin -> full text string
epub_cache: dict[str, str] = {}


def get_epub_text(asin: str) -> str | None:
    if asin not in epub_cache:
        book_info = config.BOOKS.get(asin)
        if not book_info:
            logger.warning(f"No epub configured for ASIN {asin}")
            return None
        logger.info(f"Loading epub for {book_info['title']}...")
        epub_cache[asin] = load_epub_text(book_info["epub"])
        logger.info(f"Loaded {len(epub_cache[asin])} chars")
    return epub_cache[asin]


def get_new_highlights() -> list:
    """Get all highlights not yet processed across all books."""
    all_highlights = parse_clippings(config.CLIPPINGS_PATH, config.CLIPPINGS_TITLE_TO_ASIN)
    new = [h for h in all_highlights if not state_manager.is_processed(h.annotation_id)]
    logger.debug(f"get_new_highlights: {len(all_highlights)} total, {len(new)} unprocessed, {len(state_manager.state.processed_ids)} in processed_ids")
    return new


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


def card_keyboard(annotation_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"accept:{annotation_id}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit:{annotation_id}"),
            InlineKeyboardButton("⏭ Skip", callback_data=f"skip:{annotation_id}"),
        ]
    ])


async def process_next_highlight(update: Update, context: ContextTypes.DEFAULT_TYPE, silent=False):
    """Process and send the next highlight to the user."""
    new_highlights = get_new_highlights()

    if not new_highlights:
        if not silent:
            await update.effective_message.reply_text("🎉 All highlights processed! Use /export to get your cards.")
        return None

    highlight = new_highlights[0]
    logger.debug(f"Processing highlight {highlight.annotation_id} from book {highlight.asin} loc {highlight.location_start}")
    epub_text = get_epub_text(highlight.asin)
    if epub_text is None:
        await update.effective_message.reply_text(
            f"⚠️ No epub configured for book `{highlight.asin}`.\n"
            "Add it to `BOOKS` in config.py.",
            parse_mode="Markdown"
        )
        return None

    data = find_context(epub_text, highlight.text)
    if data is None:
        logger.warning(f"Could not find '{highlight.text}' in epub, using highlight text only")
        data = {"highlight": highlight.text, "context": highlight.text}

    book_title = config.BOOKS.get(highlight.asin, {}).get("title", highlight.asin)
    await update.effective_message.reply_text(f"⏳ Generating card with Claude... _{book_title}_", parse_mode="Markdown")

    try:
        card_data = generate_card(data["highlight"], data["context"], config.ANTHROPIC_API_KEY)
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Claude error: {e}")
        return None

    card = Card(
        annotation_id=highlight.annotation_id,
        asin=highlight.asin,
        highlight=data["highlight"],
        context=data["context"],
        front=card_data.get("front", data["highlight"]),
        back=card_data.get("back", ""),
        note=card_data.get("note", ""),
    )
    state_manager.add_pending(card)
    state_manager.mark_processed(highlight.annotation_id)

    # print(format_card_message(card))  # for debugging

    await update.effective_message.reply_text(
        format_card_message(card),
        parse_mode="MarkdownV2",
        reply_markup=card_keyboard(card.annotation_id),
    )
    return card


async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_next_highlight(update, context)


async def cmd_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process N highlights: /batch 5"""
    try:
        n = int(context.args[0]) if context.args else 5
        n = min(n, 20)  # safety cap
    except (ValueError, IndexError):
        n = 5

    await update.message.reply_text(f"Processing {n} highlights...")
    for _ in range(n):
        card = await process_next_highlight(update, context, silent=True)
        if card is None:
            break
        await asyncio.sleep(1)  # be kind to the API


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new = get_new_highlights()
    s = state_manager.state

    # Per-book remaining
    from collections import Counter
    remaining_by_book = Counter(h.asin for h in new)
    book_lines = ""
    for asin, count in remaining_by_book.items():
        title = config.BOOKS.get(asin, {}).get("title", asin)
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


async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = state_manager.state.accepted_cards
    if not cards:
        await update.message.reply_text("No accepted cards yet.")
        return
    count = export_to_csv(cards, config.EXPORT_CSV)
    await update.message.reply_text(
        f"✅ Exported {count} cards to:\n`{config.EXPORT_CSV}`\n\n"
        "Import into Quizlet: Create set → Import → paste file → "
        "set 'Between term and definition' to *Tab*, 'Between rows' to *New line*",
        parse_mode="Markdown"
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
            # Auto-send next
            await process_next_highlight(update, context)

    elif action == "skip":
        state_manager.skip_card(annotation_id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("⏭ Skipped.")
        await process_next_highlight(update, context)

    elif action == "edit":
        # Find the card and prompt for edit
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
        await process_next_highlight(update, context)
    else:
        await update.message.reply_text("Card not found, may have already been processed.")


def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("next", cmd_next))
    app.add_handler(CommandHandler("batch", cmd_batch))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_message))

    logger.info("Bot started. Listening...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
