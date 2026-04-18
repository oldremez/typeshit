"""
clippings_parser.py
Parses My Clippings.txt from a connected Kindle device.
"""

import hashlib
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClippingHighlight:
    annotation_id: str   # stable hash of (book_title, location_start, text)
    asin: str
    book_title: str
    text: str
    location_start: int
    location_end: int
    added_date: str

    @property
    def sort_key(self):
        return (self.asin, self.location_start)


_SEPARATOR = "=========="
_META_RE = re.compile(r"Your Highlight.*?[Ll]ocation (\d+)-(\d+).*?\| Added on (.+)")


def _stable_id(book_title: str, location_start: int, text: str) -> str:
    key = f"{book_title}|{location_start}|{text}"
    return "cl-" + hashlib.md5(key.encode("utf-8")).hexdigest()[:12]


def parse_clippings(path: str, title_to_asin: dict[str, str]) -> list[ClippingHighlight]:
    """
    Parse My Clippings.txt and return highlights for books matched in title_to_asin.
    title_to_asin maps a title substring -> ASIN.
    """
    with open(path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    entries = content.split(_SEPARATOR)
    logger.debug(f"Clippings file: {len(content)} chars, {len(entries)} raw entries")
    logger.debug(f"Matching against title fragments: {list(title_to_asin.keys())}")

    results = []
    skipped_too_short = 0
    skipped_not_highlight = 0
    skipped_no_book_match = 0
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

        asin = next(
            (a for fragment, a in title_to_asin.items() if fragment in book_title_line),
            None,
        )
        if asin is None:
            skipped_no_book_match += 1
            continue

        m = _META_RE.search(meta_line)
        if not m:
            logger.warning(f"Meta regex did not match: {meta_line!r}")
            skipped_no_meta_match += 1
            continue

        loc_start, loc_end = int(m.group(1)), int(m.group(2))

        results.append(ClippingHighlight(
            annotation_id=_stable_id(book_title_line, loc_start, text),
            asin=asin,
            book_title=book_title_line,
            text=text,
            location_start=loc_start,
            location_end=loc_end,
            added_date=m.group(3).strip(),
        ))

    logger.debug(
        f"Parsing done: {len(results)} matched | "
        f"skipped too_short={skipped_too_short} not_highlight={skipped_not_highlight} "
        f"no_book_match={skipped_no_book_match} no_meta_match={skipped_no_meta_match}"
    )
    if results:
        logger.debug(f"First match: {results[0].book_title!r} loc={results[0].location_start} text={results[0].text!r}")

    results.sort(key=lambda h: h.sort_key)
    return results
