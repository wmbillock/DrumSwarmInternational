"""Singleton DB session pool — shared_ptr semantics.

Provides a single engine and session factory shared across the application.
Sessions are checked out via context manager and returned on exit.

Replaces the pattern of creating private engines in agent_runtime._get_critique_context()
and task_manager.TaskManager.__init__().
"""

import logging
import threading
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

_DEFAULT_DB_URL = "sqlite:///dci_swarm.db"


class DBPool:
    """Thread-safe singleton providing shared DB engine and session factory.

    Usage:
        pool = get_db_pool()
        with pool.session() as db:
            corps = db.query(Corps).all()
    """

    _instance: Optional["DBPool"] = None
    _lock = threading.Lock()

    def __new__(cls, db_url: str = _DEFAULT_DB_URL) -> "DBPool":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._engine = create_engine(db_url, echo=False)
                cls._instance._session_factory = sessionmaker(bind=cls._instance._engine)
                cls._instance._db_url = db_url
                cls._instance._checkout_count = 0
                cls._instance._count_lock = threading.Lock()
                logger.info("DBPool initialized with %s", db_url)
        return cls._instance

    @property
    def engine(self):
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        return self._session_factory

    @contextmanager
    def session(self) -> Session:
        """Check out a DB session. Automatically closed on exit."""
        with self._count_lock:
            self._checkout_count += 1

        db = self._session_factory()
        try:
            yield db
        finally:
            db.close()
            with self._count_lock:
                self._checkout_count -= 1

    def create_session(self) -> Session:
        """Create a session without context manager (caller must close).

        Prefer .session() context manager when possible.
        """
        with self._count_lock:
            self._checkout_count += 1
        return self._session_factory()

    def return_session(self, db: Session) -> None:
        """Return a session created with create_session()."""
        db.close()
        with self._count_lock:
            self._checkout_count = max(0, self._checkout_count - 1)

    @property
    def active_sessions(self) -> int:
        with self._count_lock:
            return self._checkout_count

    def get_stats(self) -> dict:
        return {
            "db_url": self._db_url,
            "active_sessions": self.active_sessions,
        }

    @classmethod
    def reset(cls):
        """Reset the singleton (for testing)."""
        with cls._lock:
            if cls._instance is not None:
                try:
                    cls._instance._engine.dispose()
                except Exception:
                    pass
                cls._instance = None


def get_db_pool(db_url: str = _DEFAULT_DB_URL) -> DBPool:
    """Get the singleton DB pool."""
    return DBPool(db_url)
