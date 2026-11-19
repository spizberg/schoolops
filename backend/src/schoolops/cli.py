"""Administrative commands.

Usage:
    python -m schoolops.cli create-admin --email admin@example.com
"""

import argparse
import asyncio
import getpass
import sys
from collections.abc import Sequence

from sqlalchemy import select

from schoolops.core.config import get_settings
from schoolops.core.security import hash_password
from schoolops.db.models import User
from schoolops.db.session import build_engine, build_sessionmaker
from schoolops.domain.enums import UserRole

MIN_PASSWORD_LENGTH = 12


async def _create_admin(email: str, password: str) -> int:
    settings = get_settings()
    engine = build_engine(settings.database_url)
    try:
        sessionmaker = build_sessionmaker(engine)
        async with sessionmaker() as session:
            normalized = email.strip().lower()
            existing = await session.scalar(select(User).where(User.email == normalized))
            if existing is not None:
                print(f"An account with email '{normalized}' already exists.", file=sys.stderr)
                return 1
            user = User(
                email=normalized,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            )
            session.add(user)
            await session.commit()
            print(f"Created admin {normalized} ({user.id}).")
            return 0
    finally:
        await engine.dispose()


def _prompt_password() -> str:
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    return password


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cbsg", description="Children's Bible Study Group admin tools"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin = subparsers.add_parser("create-admin", help="Create an administrator account")
    create_admin.add_argument("--email", required=True, help="Login email")
    create_admin.add_argument(
        "--password",
        help="Password (prompted for when omitted; prefer the prompt)",
    )
    args = parser.parse_args(argv)

    if args.command == "create-admin":
        password = args.password or _prompt_password()
        if len(password) < MIN_PASSWORD_LENGTH:
            print(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
                file=sys.stderr,
            )
            return 2
        return asyncio.run(_create_admin(args.email, password))

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
