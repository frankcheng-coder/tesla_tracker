"""Serves the Tesla third-party public key.

Tesla fetches this from your registered domain at exactly:
    https://<your-domain>/.well-known/appspecific/com.tesla.3p.public-key.pem

during partner-account registration. Generate the key pair first with:
    python -m app.tesla_setup genkey
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.config import get_settings

settings = get_settings()
router = APIRouter(tags=["meta"])


@router.get(
    "/.well-known/appspecific/com.tesla.3p.public-key.pem",
    response_class=PlainTextResponse,
)
def tesla_public_key() -> PlainTextResponse:
    path = settings.tesla_public_key_path
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=(
                "Public key not found. Generate it with "
                "`python -m app.tesla_setup genkey`."
            ),
        )
    with open(path, "r", encoding="utf-8") as f:
        pem = f.read()
    return PlainTextResponse(pem, media_type="application/x-pem-file")
