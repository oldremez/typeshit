"""
epub_reader.py
Extracts full plain text from an epub and retrieves context around a highlight.
"""

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re


def load_epub_text(epub_path: str) -> str:
    """Extract concatenated plain text from all document items in the epub."""
    book = epub.read_epub(epub_path)
    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    parts = []
    for item in items:
        soup = BeautifulSoup(item.get_content(), "html.parser")
        parts.append(soup.get_text())
    return "".join(parts)


def get_highlight_with_context(full_text: str, start: int, end: int, context_chars: int = 300) -> dict:
    """
    Given char offsets, return the highlighted text plus surrounding sentence context.
    
    Returns:
        {
            "highlight": str,       # the exact highlighted text
            "context": str,         # surrounding sentence(s)
            "context_start": int,   # where context starts in full_text
        }
    """
    highlight = full_text[start:end]

    # Expand outward to find sentence boundaries
    left = max(0, start - context_chars)
    right = min(len(full_text), end + context_chars)
    window = full_text[left:right]

    # Find the sentence containing the highlight within the window
    highlight_in_window = start - left

    # Find start of sentence (look for . ! ? \n before highlight)
    sentence_start = highlight_in_window
    for i in range(highlight_in_window - 1, -1, -1):
        if window[i] in ".!?\n" and i < highlight_in_window - 2:
            sentence_start = i + 1
            break
    else:
        sentence_start = 0

    # Find end of sentence
    sentence_end = highlight_in_window + (end - start)
    for i in range(sentence_end, len(window)):
        if window[i] in ".!?\n":
            sentence_end = i + 1
            break
    else:
        sentence_end = len(window)

    context = window[sentence_start:sentence_end].strip()

    # Clean up extra whitespace
    context = re.sub(r"\s+", " ", context)
    highlight = re.sub(r"\s+", " ", highlight).strip()

    return {
        "highlight": highlight,
        "context": context,
        "context_start": left + sentence_start,
    }
