"""Corps seeder — loads founding corps definitions from YAML into the database.

Reads data/founding_corps/*.yaml on first startup and creates corps records.
Idempotent: skips corps that already exist (matched by name).
After seeding, the database is the sole source of truth.
"""

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.corps import Corps, CorpsStatus
from backend.services.yaml_util import safe_load_yaml_dict

logger = logging.getLogger(__name__)

FOUNDING_CORPS_DIR = Path(__file__).parent.parent.parent / "data" / "founding_corps"


def seed_founding_corps(db: Session, corps_dir: Optional[Path] = None) -> list[Corps]:
    """Load founding corps from YAML into the database.

    Returns list of newly created corps (empty if all already exist).
    """
    source_dir = corps_dir or FOUNDING_CORPS_DIR
    if not source_dir.exists():
        logger.info("No founding corps directory at %s, skipping seed", source_dir)
        return []

    yaml_files = sorted(source_dir.glob("*.yaml"))
    if not yaml_files:
        logger.info("No founding corps YAML files found")
        return []

    created = []
    for path in yaml_files:
        try:
            data = safe_load_yaml_dict(path.read_text())
            if not data or not data.get("name"):
                logger.warning("Skipping %s: missing 'name' field", path.name)
                continue

            name = data["name"]

            # Idempotent: skip if already exists, but fix up stale fields
            existing = db.query(Corps).filter(Corps.name == name).first()
            if existing:
                changed = False
                if existing.corps_type != "competing":
                    existing.corps_type = "competing"
                    changed = True
                if existing.status == CorpsStatus.INITIALIZING:
                    existing.status = CorpsStatus.WINTER_CAMPS
                    changed = True
                if changed:
                    db.commit()
                    logger.info("Fixed up corps '%s': type=%s status=%s", name, existing.corps_type, existing.status.value)
                continue

            # Create the corps record
            from backend.services.corps_service import create_corps

            mascot_name = None
            if data.get("mascot"):
                mascot_name = data["mascot"].get("name")

            corps = create_corps(
                db,
                name=name,
                theme_id=data.get("theme_id", "default"),
                mascot=mascot_name,
            )

            # Founding corps are regular user corps, ready for use
            corps.status = CorpsStatus.WINTER_CAMPS
            corps.corps_type = "competing"

            # Store extended fields
            visual = data.get("visual_identity", {})
            if visual.get("uniform_concept"):
                corps.uniform_concept = visual["uniform_concept"]

            if data.get("caption_affinity"):
                corps.caption_affinity = data["caption_affinity"]

            # Persist full founding definition for reference
            import json
            corps.founding_definition = json.dumps(data, default=str)

            db.commit()
            db.refresh(corps)
            created.append(corps)
            logger.info("Seeded founding corps: %s (id=%s)", name, corps.id)

        except Exception as e:
            logger.error("Failed to seed corps from %s: %s", path.name, e)
            continue

    if created:
        logger.info("Seeded %d founding corps", len(created))
    else:
        logger.info("All founding corps already exist")

    return created
