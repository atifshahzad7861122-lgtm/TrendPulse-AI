"""Universal session manager for persistent multi-marketplace browser and HTTP states."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.crawling.models import MarketplaceType
from app.core.logging import logger


class MarketplaceSessionState(BaseModel):
    """Encapsulates authenticated / guest session state for a marketplace."""
    session_id: str
    marketplace: MarketplaceType
    cookies: Dict[str, str] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    user_agent: Optional[str] = None
    proxy: Optional[str] = None
    storage_state: Optional[Dict[str, Any]] = None  # Playwright storage state format
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


class UniversalSessionManager:
    """
    Manages session lifecycle, cookie persistence, and Playwright storage state
    across multiple ecommerce marketplaces.
    """

    def __init__(self, persistence_dir: Optional[Path] = None):
        self.persistence_dir = persistence_dir or Path("data/sessions")
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, MarketplaceSessionState] = {}
        self._load_disk_sessions()

    def _load_disk_sessions(self) -> None:
        """Load saved sessions from disk."""
        try:
            for file_path in self.persistence_dir.glob("*.json"):
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    session = MarketplaceSessionState(**data)
                    self._sessions[session.session_id] = session
                except Exception as e:
                    logger.warning(f"Failed to load session file {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Error reading session directory: {e}")

    def get_or_create_session(
        self,
        marketplace: MarketplaceType,
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> MarketplaceSessionState:
        """Retrieve existing valid session or create new one."""
        sid = session_id or f"{marketplace.value}_default"
        if sid in self._sessions:
            session = self._sessions[sid]
            session.last_used_at = datetime.now(timezone.utc)
            return session

        new_session = MarketplaceSessionState(
            session_id=sid,
            marketplace=marketplace,
            user_agent=user_agent,
        )
        self._sessions[sid] = new_session
        self.save_session(new_session)
        return new_session

    def save_session(self, session: MarketplaceSessionState) -> None:
        """Persist session state to memory and disk."""
        session.last_used_at = datetime.now(timezone.utc)
        self._sessions[session.session_id] = session
        try:
            file_path = self.persistence_dir / f"{session.session_id}.json"
            file_path.write_text(session.model_dump_json(indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to persist session {session.session_id} to disk: {e}")

    def update_cookies(self, session_id: str, cookies: Dict[str, str]) -> None:
        """Update cookie jar for session."""
        if session_id in self._sessions:
            self._sessions[session_id].cookies.update(cookies)
            self.save_session(self._sessions[session_id])
