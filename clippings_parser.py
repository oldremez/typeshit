"""
clippings_parser.py
Parses My Clippings.txt from a connected Kindle device.
"""

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClippingHighlight:
    annotation_id: str   # stable hash of (book_title, location_start, text)
    book_id: str         # stable hash of book_title
    book_title: str      # exact title as it appears in clippings
    text: str
    location_start: int
    location_end: int
    added_date: str

    @property
    def sort_key(self):
        return (self.book_id, self.location_start)


_SEPARATOR = "=========="
_META_RE = re.compile(r"Your Highlight.*?[Ll]ocation (\d+)-(\d+).*?\| Added on (.+)")


def book_id_for_title(title: str) -> str:
    return hashlib.md5(title.encode("utf-8")).hexdigest()[:12]


def _annotation_id(book_title: str, location_start: int, text: str) -> str:
    key = f"{book_title}|{location_start}|{text}"
    return "cl-" + hashlib.md5(key.encode("utf-8")).hexdigest()[:12]


def parse_clippings(path: str) -> list[ClippingHighlight]:
    """Parse My Clippings.txt and return all highlights across all books."""
    with open(path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    entries = content.split(_SEPARATOR)
    logger.debug(f"Clippings file: {len(content)} chars, {len(entries)} raw entries")

    results = []
    skipped_too_short = 0
    skipped_not_highlight = 0
    skipped_no_meta_match = 0

    for entry in entries:
        lines = [l.strip() for l in entry.strip().splitlines() if l.strip()]
        if len(lines) < 3:
            skipped_too_short += 1
            continue

        book_title_line = lines[0]
        meta_line = lines[1]
        text = " ".join(lines[2:])

        if "Your Highlight" not in meta_line:
            skipped_not_highlight += 1
            continue

        m = _META_RE.search(meta_line)
        if not m:
            logger.warning(f"Meta regex did not match: {meta_line!r}")
            skipped_no_meta_match += 1
            continue

        loc_start, loc_end = int(m.group(1)), int(m.group(2))

        results.append(ClippingHighlight(
            annotation_id=_annotation_id(book_title_line, loc_start, text),
            book_id=book_id_for_title(book_title_line),
            book_title=book_title_line,
            text=text,
            location_start=loc_start,
            location_end=loc_end,
            added_date=m.group(3).strip(),
        ))

    logger.debug(
        f"Parsing done: {len(results)} highlights | "
        f"skipped too_short={skipped_too_short} not_highlight={skipped_not_highlight} "
        f"no_meta_match={skipped_no_meta_match}"
    )

    results.sort(key=lambda h: h.sort_key)
    return results


def discover_books(clippings_path: str, books_json_path: str) -> list[str]:
    """
    Parse clippings and add any newly seen books to books.json.
    Returns list of newly added book titles.
    """
    highlights = parse_clippings(clippings_path)

    if os.path.exists(books_json_path):
        with open(books_json_path, "r", encoding="utf-8") as f:
            books = json.load(f)
    else:
        books = {}

    new_titles = []
    for h in highlights:
        if h.book_id not in books:
            books[h.book_id] = {
                "title": h.book_title,
                "clippings_title": h.book_title,
                "epub": "",
            }
            new_titles.append(h.book_title)
            logger.info(f"Discovered new book: {h.book_title!r} (id={h.book_id})")

    if new_titles:
        with open(books_json_path, "w", encoding="utf-8") as f:
            json.dump(books, f, ensure_ascii=False, indent=2)

    return new_titles
