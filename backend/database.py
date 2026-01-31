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
