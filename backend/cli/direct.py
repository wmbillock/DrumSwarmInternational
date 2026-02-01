"""Direct DB/service calls for offline mode — no API server needed."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database import Base


class DirectClient:
    """Directly accesses the database and services when the API is not running."""

    def __init__(self, db_url: str = "sqlite:///dci_swarm.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(bind=self.engine)

    def _session(self) -> Session:
        return self._session_factory()

    # --- Season ---
    def season_create(self, name: str, year: int | None = None) -> dict:
        from pathlib import Path
        from backend.services.season_persistence import create_season
        season_id = name.lower().replace(" ", "_")
        if year:
            season_id = f"{season_id}_{year}"
        season_dir = create_season(Path("."), season_id, metadata={"name": name, "year": year})
        return {"season_id": season_id, "path": str(season_dir), "name": name, "year": year}

    # --- Corps ---
    def corps_list(self, season_id: str | None = None) -> list:
        from backend.models.show import Show
        db = self._session()
        try:
            shows = db.query(Show).all()
            return [{"id": s.id, "title": s.title, "status": s.status.value, "corps_id": s.corps_id} for s in shows]
        finally:
            db.close()

    def corps_status(self, corps_id: str) -> dict:
        from backend.models.corps import Corps
        db = self._session()
        try:
            corps = db.get(Corps, corps_id)
            if not corps:
                return {"error": "Corps not found"}
            return {
                "id": corps.id, "name": corps.name, "status": corps.status.value,
                "mode": corps.mode.value if corps.mode else None,
                "rehearsal_mode": corps.rehearsal_mode.value if corps.rehearsal_mode else None,
            }
        finally:
            db.close()

    # --- Shows ---
    def show_create(self, title: str, description: str | None = None) -> dict:
        from backend.services.show_service import create_show
        db = self._session()
        try:
            show = create_show(db, title=title, description=description)
            return {"id": show.id, "title": show.title, "status": show.status.value}
        finally:
            db.close()

    def show_activate(self, show_id: str) -> dict:
        from backend.services.show_service import activate_show
        db = self._session()
        try:
            show = activate_show(db, show_id)
            return {"id": show.id, "status": show.status.value, "corps_id": show.corps_id}
        finally:
            db.close()

    def show_list(self) -> list:
        from backend.models.show import Show
        db = self._session()
        try:
            shows = db.query(Show).all()
            return [{"id": s.id, "title": s.title, "status": s.status.value, "corps_id": s.corps_id} for s in shows]
        finally:
            db.close()

    # --- Mode ---
    def mode_switch(self, corps_id: str, mode: str) -> dict:
        from backend.models.corps import CorpsMode
        from backend.services.mode_manager import switch_mode
        db = self._session()
        try:
            corps = switch_mode(db, corps_id, CorpsMode(mode))
            return {"id": corps.id, "mode": corps.mode.value}
        finally:
            db.close()

    # --- Status / Health ---
    def system_health(self) -> dict:
        from backend.services.system_health import get_swarm_health
        import dataclasses
        db = self._session()
        try:
            health = get_swarm_health(db)
            return dataclasses.asdict(health)
        finally:
            db.close()

    # --- Work log ---
    def work_log(self, corps_id: str, limit: int = 50) -> list:
        from backend.models.work_log import WorkLog
        db = self._session()
        try:
            logs = db.query(WorkLog).filter(WorkLog.corps_id == corps_id).order_by(
                WorkLog.timestamp.desc()
            ).limit(limit).all()
            return [{"id": l.id, "role": l.role, "event_type": l.event_type, "details": l.details} for l in logs]
        finally:
            db.close()

    def global_log(self, limit: int = 50) -> list:
        from backend.models.work_log import WorkLog
        db = self._session()
        try:
            logs = db.query(WorkLog).order_by(WorkLog.timestamp.desc()).limit(limit).all()
            return [{"id": l.id, "role": l.role, "event_type": l.event_type, "details": l.details} for l in logs]
        finally:
            db.close()
