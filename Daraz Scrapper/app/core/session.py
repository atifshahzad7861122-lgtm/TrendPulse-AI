"""Reusable session and state persistence management for HTTP and Browser contexts."""

import asyncio
from dataclasses import dataclass, field
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from app.core.exceptions import SessionError
from app.core.logging import logger


@dataclass
class SessionState:
    """Represents a serialized session container."""
    session_id: str
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    cookies: List[Dict[str, Any]] = field(default_factory=list)
    storage_state: Dict[str, Any] = field(default_factory=dict)
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class SessionManager:
    """Manages lifecycle, persistence, and isolation of HTTP and Browser session states."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        default_ttl_seconds: float = 86400.0,  # 24 hours
    ):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self.default_ttl_seconds = default_ttl_seconds
        self._sessions: Dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

        if self.storage_dir:
            self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def get_or_create_session(
        self,
        session_id: str,
        user_agent: Optional[str] = None,
    ) -> SessionState:
        """Retrieve existing active session or instantiate a new one."""
        async with self._lock:
            # 1. Check in-memory store
            if session_id in self._sessions:
                sess = self._sessions[session_id]
                if not sess.is_expired:
                    return sess
                logger.info(f"Session '{session_id}' expired. Recreating.", extra={"event": "session_expired"})

            # 2. Check disk store if configured
            if self.storage_dir:
                file_path = self.storage_dir / f"{session_id}.json"
                if file_path.exists():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        sess = SessionState(**data)
                        if not sess.is_expired:
                            self._sessions[session_id] = sess
                            return sess
                    except Exception as e:
                        logger.warning(f"Failed to load session file {file_path}: {e}")

            # 3. Create fresh session
            new_sess = SessionState(
                session_id=session_id,
                created_at=time.time(),
                expires_at=time.time() + self.default_ttl_seconds,
                user_agent=user_agent,
            )
            self._sessions[session_id] = new_sess
            return new_sess

    def _save_session_unlocked(self, session: SessionState) -> None:
        """Internal save routine assuming lock is held."""
        self._sessions[session.session_id] = session
        if self.storage_dir:
            file_path = self.storage_dir / f"{session.session_id}.json"
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "session_id": session.session_id,
                            "created_at": session.created_at,
                            "expires_at": session.expires_at,
                            "cookies": session.cookies,
                            "storage_state": session.storage_state,
                            "user_agent": session.user_agent,
                            "metadata": session.metadata,
                        },
                        f,
                        indent=2,
                    )
            except Exception as e:
                raise SessionError(f"Failed to persist session to disk: {e}") from e

    async def save_session(self, session: SessionState) -> None:
        """Persist session state in-memory and to disk if configured."""
        async with self._lock:
            self._save_session_unlocked(session)

    async def update_cookies(self, session_id: str, cookies: List[Dict[str, Any]]) -> None:
        """Update cookie list for the session."""
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].cookies = cookies
                self._save_session_unlocked(self._sessions[session_id])

    async def update_storage_state(self, session_id: str, storage_state: Dict[str, Any]) -> None:
        """Update Playwright storage_state for the session."""
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].storage_state = storage_state
                if "cookies" in storage_state:
                    self._sessions[session_id].cookies = storage_state["cookies"]
                self._save_session_unlocked(self._sessions[session_id])

    async def clear_session(self, session_id: str) -> None:
        """Remove and delete session from memory and disk."""
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
            if self.storage_dir:
                file_path = self.storage_dir / f"{session_id}.json"
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
