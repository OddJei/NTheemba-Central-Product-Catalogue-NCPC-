import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ncpc_service.api import app
from ncpc_service.auth import Principal, token_digest
from ncpc_service.database import get_session
from ncpc_service.enums import PrincipalRole
from ncpc_service.models import ApiClient, Base

BUSINESS_A_TOKEN = "business-a-token-that-is-long-enough"
BUSINESS_B_TOKEN = "business-b-token-that-is-long-enough"
ADMIN_TOKEN = "admin-token-that-is-long-enough-for-tests"
NTHEEMBA_TOKEN = "ntheemba-token-that-is-long-enough"


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    with factory() as value:
        value.add_all(
            [
                ApiClient(
                    client_id="business-a",
                    token_digest=token_digest(BUSINESS_A_TOKEN),
                    role=PrincipalRole.BUSINESS,
                    business_id="business-a",
                    scopes=[
                        "catalogue:read",
                        "submissions:write",
                        "submissions:read",
                        "coverage:read",
                        "coverage:write",
                    ],
                ),
                ApiClient(
                    client_id="business-b",
                    token_digest=token_digest(BUSINESS_B_TOKEN),
                    role=PrincipalRole.BUSINESS,
                    business_id="business-b",
                    scopes=[
                        "catalogue:read",
                        "submissions:write",
                        "submissions:read",
                        "coverage:read",
                        "coverage:write",
                    ],
                ),
                ApiClient(
                    client_id="admin",
                    token_digest=token_digest(ADMIN_TOKEN),
                    role=PrincipalRole.ADMIN,
                    scopes=["*"],
                ),
                ApiClient(
                    client_id="ntheemba",
                    token_digest=token_digest(NTHEEMBA_TOKEN),
                    role=PrincipalRole.NTHEEMBA,
                    scopes=["catalogue:read", "coverage:read", "discovery:read"],
                ),
            ]
        )
        value.commit()
        yield value
    Base.metadata.drop_all(engine)


@pytest.fixture()
def principals() -> dict[str, Principal]:
    return {
        "business_a": Principal(
            "business-a",
            PrincipalRole.BUSINESS,
            "business-a",
            frozenset(
                {
                    "catalogue:read",
                    "submissions:write",
                    "submissions:read",
                    "coverage:read",
                    "coverage:write",
                }
            ),
        ),
        "business_b": Principal(
            "business-b",
            PrincipalRole.BUSINESS,
            "business-b",
            frozenset(
                {
                    "catalogue:read",
                    "submissions:write",
                    "submissions:read",
                    "coverage:read",
                    "coverage:write",
                }
            ),
        ),
        "admin": Principal("admin", PrincipalRole.ADMIN, None, frozenset({"*"})),
        "ntheemba": Principal(
            "ntheemba",
            PrincipalRole.NTHEEMBA,
            None,
            frozenset({"catalogue:read", "coverage:read", "discovery:read"}),
        ),
    }


@pytest.fixture()
def client(session: Session) -> TestClient:
    def override_session():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
