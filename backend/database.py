from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def create_db_engine(db_url: str = "sqlite:///dci_swarm.db"):
    return create_engine(db_url, echo=False)


def create_session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)
