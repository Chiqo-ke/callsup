from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .models import Base


def create_sqlalchemy_engine(settings: Settings):
    connect_args = {"check_same_thread": False} if settings.callsup_platform_db_dsn.startswith("sqlite") else {}
    return create_engine(settings.callsup_platform_db_dsn, future=True, connect_args=connect_args)


def create_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session, future=True)


def initialize_database(engine) -> None:
    Base.metadata.create_all(bind=engine)


def is_database_ready(engine) -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True

