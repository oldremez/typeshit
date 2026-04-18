"""
state.py
Persists the bot's progress: last processed highlight, pending and accepted cards.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Card:
    annotation_id: str
    asin: str
    highlight: str
    context: str
    front: str          # normalized Greek form
    back: str           # English translation
    note: str           # usage note
    status: str = "pending"   # pending | accepted | skipped


@dataclass
class BotState:
    processed_ids: list[str] = field(default_factory=list)
    pending_cards: list[Card] = field(default_factory=list)
    accepted_cards: list[Card] = field(default_factory=list)


class StateManager:
    def __init__(self, state_file: str):
        self.state_file = state_file
        self._state = self._load()

    def _load(self) -> BotState:
        if not os.path.exists(self.state_file):
            return BotState()
        with open(self.state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        state = BotState(
            processed_ids=data.get("processed_ids", []),
            pending_cards=[Card(**c) for c in data.get("pending_cards", [])],
            accepted_cards=[Card(**c) for c in data.get("accepted_cards", [])],
        )
        return state

    def save(self):
        data = {
            "processed_ids": self._state.processed_ids,
            "pending_cards": [asdict(c) for c in self._state.pending_cards],
            "accepted_cards": [asdict(c) for c in self._state.accepted_cards],
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @property
    def state(self) -> BotState:
        return self._state

    def mark_processed(self, annotation_id: str):
        if annotation_id not in self._state.processed_ids:
            self._state.processed_ids.append(annotation_id)
        self.save()

    def is_processed(self, annotation_id: str) -> bool:
        return annotation_id in self._state.processed_ids

    def add_pending(self, card: Card):
        self._state.pending_cards.append(card)
        self.save()

    def accept_card(self, annotation_id: str, front: str = None, back: str = None, note: str = None):
        for card in self._state.pending_cards:
            if card.annotation_id == annotation_id:
                if front:
                    card.front = front
                if back:
                    card.back = back
                if note:
                    card.note = note
                card.status = "accepted"
                self._state.pending_cards.remove(card)
                self._state.accepted_cards.append(card)
                self.save()
                return card
        return None

    def skip_card(self, annotation_id: str):
        for card in self._state.pending_cards:
            if card.annotation_id == annotation_id:
                card.status = "skipped"
                self._state.pending_cards.remove(card)
                self.save()
                return
