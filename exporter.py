"""
exporter.py
Exports accepted cards to a CSV file importable by Quizlet.

Quizlet CSV format:
  - One card per line
  - Term and definition separated by a tab (or comma)
  - Cards separated by newline
  - Import settings in Quizlet: "between term and definition: Tab", "between cards: New line"
"""

import csv
import os
from state import Card


def export_to_csv(cards: list[Card], output_path: str):
    """Export accepted cards to Quizlet-compatible CSV."""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        for card in cards:
            # Front: normalized Greek form
            # Back: translation + optional note
            back = card.back
            if card.note:
                back = f"{card.back} | {card.note}"
            writer.writerow([card.front, back])

    return len(cards)


def export_with_context(cards: list[Card], output_path: str):
    """Export with full context as a readable reference CSV."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Greek (normalized)", "English", "Note", "Original highlight", "Context"])
        for card in cards:
            writer.writerow([card.front, card.back, card.note, card.highlight, card.context])
    return len(cards)
