from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import ApiClient, Base, IdSequence


def create_ncpc_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


engine = create_ncpc_engine()
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def get_session() -> Generator[Session, None, None]:
    with SessionFactory() as session:
        yield session


@contextmanager
def transaction(session: Session) -> Generator[Session, None, None]:
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


def next_public_id(session: Session, namespace: str, width: int = 6) -> str:
    row = session.scalar(select(IdSequence).where(IdSequence.namespace == namespace).with_for_update())
    if row is None:
        row = IdSequence(namespace=namespace, next_value=2)
        session.add(row)
        value = 1
    else:
        value = row.next_value
        row.next_value += 1
    session.flush()
    return f"{namespace}-{value:0{width}d}"


def create_schema_for_tests(target_engine: Engine) -> None:
    Base.metadata.create_all(target_engine)


def seed_api_client(session: Session, client: ApiClient) -> ApiClient:
    existing = session.get(ApiClient, client.client_id)
    if existing is not None:
        return existing
    session.add(client)
    session.flush()
    return client
