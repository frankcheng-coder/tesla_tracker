"""One-time Tesla Fleet API setup helpers.

Subcommands:
    genkey            Generate the EC (prime256v1) key pair Tesla requires.
    register-partner  Register your domain with Tesla (one-time, needs creds).
    check             Print current config + verify the public key is reachable.

Usage:
    python -m app.tesla_setup genkey
    python -m app.tesla_setup register-partner
    python -m app.tesla_setup check

None of this controls a vehicle — it only sets up read-only API access.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.config import get_settings

settings = get_settings()


def cmd_genkey() -> None:
    """Generate an EC prime256v1 key pair in the configured key paths."""
    priv_path = settings.tesla_private_key_path
    pub_path = settings.tesla_public_key_path
    os.makedirs(os.path.dirname(priv_path) or ".", exist_ok=True)

    if os.path.exists(priv_path):
        print(f"Private key already exists at {priv_path} — not overwriting.")
        return

    private_key = ec.generate_private_key(ec.SECP256R1())
    with open(priv_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(pub_path, "wb") as f:
        f.write(
            private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
    os.chmod(priv_path, 0o600)
    print(f"Wrote private key -> {priv_path} (mode 600)")
    print(f"Wrote public  key -> {pub_path}")
    print(
        "\nThe running server will host the public key at:\n"
        "  /.well-known/appspecific/com.tesla.3p.public-key.pem"
    )


def _get_partner_token() -> str:
    """client_credentials grant -> a partner (app-level) token."""
    if not (settings.tesla_client_id and settings.tesla_client_secret):
        sys.exit("TESLA_CLIENT_ID / TESLA_CLIENT_SECRET are not set in .env")
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.tesla_client_id,
        "client_secret": settings.tesla_client_secret,
        "scope": " ".join(settings.tesla_scopes),
        "audience": settings.tesla_audience,
    }
    resp = httpx.post(settings.tesla_token_url, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def cmd_register_partner() -> None:
    """Register your developer domain with Tesla (one-time per domain)."""
    if not settings.tesla_developer_domain:
        sys.exit("TESLA_DEVELOPER_DOMAIN is not set in .env")

    token = _get_partner_token()
    url = f"{settings.tesla_audience.rstrip('/')}/api/1/partner_accounts"
    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"domain": settings.tesla_developer_domain},
        timeout=30,
    )
    print(f"POST {url} -> {resp.status_code}")
    print(resp.text)
    if resp.is_success:
        print(
            "\nPartner registered. Tesla fetched your public key from "
            f"https://{settings.tesla_developer_domain}/.well-known/appspecific/"
            "com.tesla.3p.public-key.pem"
        )
    else:
        print(
            "\nIf this failed: confirm the server is reachable at your public "
            "domain and that the public key URL above returns your PEM."
        )


def cmd_check() -> None:
    print("Config:")
    print(f"  audience        = {settings.tesla_audience}")
    print(f"  developer_domain= {settings.tesla_developer_domain or '(unset)'}")
    print(f"  redirect_uri    = {settings.tesla_redirect_uri or '(unset)'}")
    print(f"  client_id set   = {bool(settings.tesla_client_id)}")
    print(f"  scopes          = {' '.join(settings.tesla_scopes)}")
    print(f"  public key file = {settings.tesla_public_key_path} "
          f"({'exists' if os.path.exists(settings.tesla_public_key_path) else 'MISSING'})")
    if settings.tesla_developer_domain:
        url = (f"https://{settings.tesla_developer_domain}"
               "/.well-known/appspecific/com.tesla.3p.public-key.pem")
        try:
            r = httpx.get(url, timeout=15)
            ok = r.is_success and "BEGIN PUBLIC KEY" in r.text
            print(f"  public key URL  = {url} -> {r.status_code} "
                  f"({'OK' if ok else 'NOT SERVING PEM'})")
        except Exception as exc:
            print(f"  public key URL  = {url} -> unreachable ({exc})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tesla Fleet API setup helpers")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("genkey", help="Generate the EC key pair")
    sub.add_parser("register-partner", help="Register your domain with Tesla")
    sub.add_parser("check", help="Print config + verify public key URL")
    args = parser.parse_args()

    {
        "genkey": cmd_genkey,
        "register-partner": cmd_register_partner,
        "check": cmd_check,
    }[args.command]()


if __name__ == "__main__":
    main()
