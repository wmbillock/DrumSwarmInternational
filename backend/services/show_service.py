"""Show management — CRUD, corps lifecycle, judge pool."""

import random
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.show import Show, ShowStatus
from backend.models.coordinate import CoordinateType
from backend.services.coordinate_service import create_coordinate
from backend.services.corps_service import create_corps, initialize_corps, start_tour, stop_tour

# Whimsical DCI-inspired corps names
CORPS_NAMES = [
    "Phantom Regiment",
    "Blue Devils",
    "Carolina Crown",
    "The Cadets",
    "Santa Clara Vanguard",
    "Bluecoats",
    "Blue Stars",
    "Boston Crusaders",
    "The Cavaliers",
    "Crossmen",
    "Madison Scouts",
    "Colts",
    "Spirit of Atlanta",
    "Troopers",
    "Mandarins",
    "Pacific Crest",
    "Blue Knights",
    "Glassmen",
    "Pioneer",
    "Velvet Knights",
    "Star of Indiana",
    "Sky Ryders",
    "Freelancers",
    "Bridgemen",
    "27th Lancers",
    "Suncoast Sound",
    "Phantom Thunder",
    "Iron Guard",
    "Crimson Cascade",
    "Midnight Suns",
    "Golden Sabres",
    "Emerald Knights",
    "Silver Stallions",
    "Copper Fury",
    "Obsidian Regiment",
    "Azure Falcons",
    "Scarlet Horizon",
    "Titanium Vanguard",
]


class ShowError(Exception):
    pass


def create_show(
    db: Session, title: str, description: Optional[str] = None
) -> Show:
    show = Show(title=title, description=description)
    db.add(show)
    db.commit()
    db.refresh(show)

    # Create root coordinate
    root = create_coordinate(db, type=CoordinateType.SHOW, title=title, description=description)
    show.coordinate_root_id = root.id
    db.commit()
    db.refresh(show)
    return show


def get_show(db: Session, show_id: str) -> Optional[Show]:
    return db.get(Show, show_id)


def list_shows(db: Session) -> list[Show]:
    return db.query(Show).order_by(Show.created_at.desc()).all()


def update_show(db: Session, show_id: str, **kwargs) -> Show:
    show = db.get(Show, show_id)
    if show is None:
        raise ShowError(f"Show {show_id} not found")
    for k, v in kwargs.items():
        if hasattr(show, k):
            setattr(show, k, v)
    db.commit()
    db.refresh(show)
    return show


def activate_show(db: Session, show_id: str) -> Show:
    """Activate a show — spawns a corps and initializes the hierarchy."""
    show = db.get(Show, show_id)
    if show is None:
        raise ShowError(f"Show {show_id} not found")
    if show.status != ShowStatus.DRAFT:
        raise ShowError(f"Can only activate draft shows, got {show.status.value}")

    corps_name = random.choice(CORPS_NAMES)
    corps = create_corps(db, name=corps_name, show_id=show.id)
    initialize_corps(db, corps.id)
    show.corps_id = corps.id
    show.status = ShowStatus.ACTIVE
    db.commit()
    db.refresh(show)
    return show


def complete_show(db: Session, show_id: str) -> Show:
    show = db.get(Show, show_id)
    if show is None:
        raise ShowError(f"Show {show_id} not found")
    show.status = ShowStatus.COMPLETED
    db.commit()
    db.refresh(show)
    return show


def archive_show(db: Session, show_id: str) -> Show:
    show = db.get(Show, show_id)
    if show is None:
        raise ShowError(f"Show {show_id} not found")
    show.status = ShowStatus.ARCHIVED
    db.commit()
    db.refresh(show)
    return show


def toggle_tour(db: Session, show_id: str, enable: bool) -> Show:
    """Toggle tour mode for a show's corps."""
    show = db.get(Show, show_id)
    if show is None:
        raise ShowError(f"Show {show_id} not found")
    if show.corps_id is None:
        raise ShowError("Show has no corps — activate it first")
    if enable:
        start_tour(db, show.corps_id)
    else:
        stop_tour(db, show.corps_id)
    return show
