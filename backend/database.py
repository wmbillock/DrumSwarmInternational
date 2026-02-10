import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def create_db_engine(db_url: str = "sqlite:///dci_swarm.db"):
    return create_engine(db_url, echo=False)


def create_session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine)


def init_db(engine) -> None:
    """Initialize database — run Alembic migrations, then create any new tables."""
    try:
        from alembic.config import Config
        from alembic import command
        import os

        ini_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
        if os.path.exists(ini_path):
            alembic_cfg = Config(ini_path)
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations applied")
        else:
            logger.warning("alembic.ini not found at %s, falling back to create_all", ini_path)
            Base.metadata.create_all(engine)
    except Exception as e:
        logger.warning("Alembic migration failed (%s), falling back to create_all", e)
        Base.metadata.create_all(engine)

    # Add missing columns to existing tables (handles schema drift without migrations)
    _apply_schema_patches(engine)


def _apply_schema_patches(engine) -> None:
    """Add columns that may be missing from existing databases."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    patches = [
        ("agent_sessions", "performer_id", "VARCHAR(36)"),
        ("scores", "rep_score", "FLOAT"),
        ("scores", "perf_score", "FLOAT"),
        # judges_tapes and critique_sessions are created by create_all
        ("corps", "corps_type", "VARCHAR(20) DEFAULT 'competing'"),
        ("critique_sessions", "is_automated", "BOOLEAN DEFAULT 0"),
        ("corps", "color_scheme", "TEXT"),
    ]

    with engine.connect() as conn:
        for table_name, column_name, column_type in patches:
            if table_name not in inspector.get_table_names():
                continue
            existing_columns = {c["name"] for c in inspector.get_columns(table_name)}
            if column_name not in existing_columns:
                try:
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                    ))
                    conn.commit()
                    logger.info("Added column %s.%s", table_name, column_name)
                except Exception as e:
                    logger.warning("Failed to add column %s.%s: %s", table_name, column_name, e)

        # Mark the admin corps as system type (only targets 'Critique', not user corps)
        try:
            conn.execute(text("UPDATE corps SET corps_type = 'system' WHERE show_id IS NULL AND name = 'Critique' AND (corps_type IS NULL OR corps_type = 'competing')"))
            conn.commit()
        except Exception as e:
            logger.debug("Corps type backfill skipped: %s", e)

        # Backfill color_scheme for existing corps that don't have one
        if "corps" in inspector.get_table_names():
            existing_cols = {c["name"] for c in inspector.get_columns("corps")}
            if "color_scheme" in existing_cols:
                try:
                    from sqlalchemy import text as _t
                    rows = conn.execute(_t("SELECT id, name FROM corps WHERE color_scheme IS NULL")).fetchall()
                    if rows:
                        import colorsys
                        import hashlib
                        import json
                        for row_id, row_name in rows:
                            h = int(hashlib.sha256(row_name.encode()).hexdigest()[:8], 16)
                            hue = h % 360
                            r, g, b = colorsys.hls_to_rgb(hue / 360.0, 0.25, 0.7)
                            primary = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
                            r, g, b = colorsys.hls_to_rgb(((hue + 30) % 360) / 360.0, 0.45, 0.5)
                            secondary = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
                            r, g, b = colorsys.hls_to_rgb(((hue + 180) % 360) / 360.0, 0.55, 0.8)
                            accent = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
                            scheme = json.dumps({"primary": primary, "secondary": secondary, "accent": accent})
                            conn.execute(_t("UPDATE corps SET color_scheme = :scheme WHERE id = :id"), {"scheme": scheme, "id": row_id})
                        conn.commit()
                        logger.info("Backfilled color_scheme for %d corps", len(rows))
                except Exception as e:
                    logger.debug("Color scheme backfill skipped: %s", e)
