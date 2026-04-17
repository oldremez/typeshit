"""
card_generator.py
Uses Claude API to prepare a Greek→Russian flashcard from a highlight + context.
"""

import anthropic
import json


SYSTEM_PROMPT = """You are a Greek language expert helping a learner create Anki/Quizlet flashcards.

Given a highlighted Greek word or phrase and its sentence context, produce a flashcard with:
- front: the normalized (dictionary/lemma) form of the word or phrase
- back: the Russian translation, concise and accurate
- note: a brief usage note — grammar info (e.g. verb conjugation, noun case),
  idiomatic meaning, or why this form is interesting

Rules:
- If a verb is highlighted in a conjugated form, front should be the infinitive/1st person present
- If a noun is in an oblique case, front should be the nominative
- If it's a phrase or idiom, keep the phrase as-is but normalized
- Keep back to 1-5 words when possible
- Keep note under 15 words
- Respond ONLY with valid JSON, no markdown, no extra text

Example response:
{"front": "αγαπώ", "back": "я люблю / любить", "note": "Common verb; irregular in some tenses"}
"""


def generate_card(highlight: str, context: str, api_key: str) -> dict:
    """
    Call Claude to generate a flashcard for the given highlight.
    Returns dict with keys: front, back, note
    """
    client = anthropic.Anthropic(api_key=api_key)

    user_message = f"""Highlighted text: «{highlight}»

Full sentence context:
{context}

Generate a flashcard for this Greek word/phrase."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text.strip()
    
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    
    card_data = json.loads(text)
    return card_data
