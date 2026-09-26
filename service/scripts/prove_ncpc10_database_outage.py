"""Verify the local NCPC v1 outage envelope while PostgreSQL is unavailable."""

from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main() -> None:
    request = Request(
        "http://127.0.0.1:8080/v1/catalogue/candidates?query=ncpc10",
        headers={
            "Authorization": "Bearer ncpc-proof-bootstrap-token-local-only",
            "X-Request-ID": "ncpc10-db-outage",
        },
    )
    try:
        urlopen(request, timeout=10)
    except HTTPError as error:
        body = json.loads(error.read())
        assert error.code == 503
        assert body["request_id"] == "ncpc10-db-outage"
        assert body["error"] == {
            "code": "DATABASE_UNAVAILABLE",
            "message": "database temporarily unavailable",
        }
        print("NCPC10_DATABASE_UNAVAILABLE_SAFE_FAILURE_PROVED")
        return
    raise AssertionError("database outage unexpectedly returned a success response")


if __name__ == "__main__":
    main()
