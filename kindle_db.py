"""
kindle_db.py
Reads highlights from the Kindle for Mac annotation SQLite database.
"""

import sqlite3
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class Highlight:
    annotation_id: str
    book_id: str
    asin: str
    start_position: int
    end_position: int
    created_time: int       # milliseconds epoch
    modified_time: int

    @property
    def sort_key(self):
        return (self.asin, self.start_position)


def read_highlights(db_path: str, book_asin: Optional[str] = None) -> list[Highlight]:
    """
    Read all HIGHLIGHT annotations from server_view, optionally filtered by book ASIN.
    Returns list sorted by start_position.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT annotation_id, dataset_id, serialized_payload, created_time, modified_time
        FROM server_view
        WHERE dataset = 1
        ORDER BY created_time ASC
    """)

    highlights = []
    for row in cur.fetchall():
        payload = json.loads(row["serialized_payload"])
        if payload.get("type") != "HIGHLIGHT":
            continue

        asin = payload.get("book_data", {}).get("asin", "")
        if book_asin and asin != book_asin:
            continue

        start = payload.get("start_position", {}).get("shortPosition")
        end = payload.get("end_position", {}).get("shortPosition")
        if start is None or end is None:
            continue

        highlights.append(Highlight(
            annotation_id=row["annotation_id"],
            book_id=row["dataset_id"],
            asin=asin,
            start_position=start,
            end_position=end,
            created_time=row["created_time"],
            modified_time=row["modified_time"],
        ))

    conn.close()
    # Sort by book then position so we process each book sequentially
    highlights.sort(key=lambda h: (h.asin, h.start_position))
    return highlights


def get_book_asins(db_path: str) -> list[str]:
    """Return all unique book ASINs that have highlights."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT dataset_id FROM server_view WHERE dataset = 1")
    rows = cur.fetchall()
    conn.close()
    # dataset_id format: ASIN-TYPE-GUID-N, extract ASIN
    asins = set()
    for (dataset_id,) in rows:
        parts = dataset_id.split("-")
        if parts:
            asins.add(parts[0])
    return list(asins)
