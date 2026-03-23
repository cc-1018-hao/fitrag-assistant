from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Dict, List


class InMemorySessionStore:
    def __init__(self) -> None:
        self._data: Dict[str, List[dict]] = defaultdict(list)
        self._lock = Lock()

    def add_user_message(self, session_id: str, content: str) -> None:
        with self._lock:
            self._data[session_id].append({"role": "user", "content": content})

    def add_assistant_message(self, session_id: str, content: str) -> None:
        with self._lock:
            self._data[session_id].append({"role": "assistant", "content": content})

    def get_recent_messages(self, session_id: str, max_turns: int) -> List[dict]:
        with self._lock:
            msgs = self._data.get(session_id, [])
            return msgs[-max_turns:]


session_store = InMemorySessionStore()
