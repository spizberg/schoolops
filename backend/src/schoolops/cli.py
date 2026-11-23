"""Administrative commands.

Usage:
    python -m schoolops.cli create-admin --email admin@example.com
    python -m schoolops.cli seed-demo
"""

import asyncio
from collections.abc import Coroutine, Sequence
from typing import Annotated, Any

import typer
from sqlalchemy import select

from schoolops.core.config import get_settings
from schoolops.core.security import hash_password
from schoolops.db.models import User
from schoolops.db.session import build_engine, build_sessionmaker
from schoolops.domain.enums import UserRole
from schoolops.seed import DemoDataExistsError
from schoolops.seed import seed_demo as seed_demo_data

MIN_PASSWORD_LENGTH = 12

app = typer.Typer(
    name="cbsg",
    help="Children's Bible Study Group admin tools.",
    no_args_is_help=True,
    add_completion=False,
)


async def _seed_demo() -> int:
    settings = get_settings()
    engine = build_engine(settings.database_url)
    try:
        sessionmaker = build_sessionmaker(engine)
        async with sessionmaker() as session:
            try:
                result = await seed_demo_data(session)
            except DemoDataExistsError as exc:
                typer.echo(str(exc), err=True)
                return 1
            typer.echo(
                "Demo data created: "
                f"{result.ministry_years} ministry years, "
                f"{result.volunteers} volunteers, "
                f"{result.households} households, "
                f"{result.guardians} guardians, "
                f"{result.children} children, "
                f"{result.classes} classes, "
                f"{result.enrollments} enrollments, "
                f"{result.sessions} sessions, "
                f"{result.session_volunteers} session volunteers, "
                f"{result.attendance} attendance records, "
                f"{result.visitors} visitors."
            )
            return 0
    finally:
        await engine.dispose()


async def _create_admin(email: str, password: str) -> int:
    settings = get_settings()
    engine = build_engine(settings.database_url)
    try:
        sessionmaker = build_sessionmaker(engine)
        async with sessionmaker() as session:
            normalized = email.strip().lower()
            existing = await session.scalar(select(User).where(User.email == normalized))
            if existing is not None:
                typer.echo(f"An account with email '{normalized}' already exists.", err=True)
                return 1
            user = User(
                email=normalized,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            )
            session.add(user)
            await session.commit()
            typer.echo(f"Created admin {normalized} ({user.id}).")
            return 0
    finally:
        await engine.dispose()


def _run(coroutine: Coroutine[Any, Any, int]) -> None:
    """Run an async command and exit with its return code."""
    raise typer.Exit(code=asyncio.run(coroutine))


@app.command("create-admin")
def create_admin(
    email: Annotated[str, typer.Option("--email", help="Login email.", prompt=True)],
    password: Annotated[
        str | None,
        typer.Option(
            "--password",
            help="Password (prompted for when omitted; prefer the prompt).",
        ),
    ] = None,
) -> None:
    """Create an administrator account."""
    chosen = password or typer.prompt("Password", hide_input=True, confirmation_prompt=True)
    if len(chosen) < MIN_PASSWORD_LENGTH:
        typer.echo(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", err=True)
        raise typer.Exit(code=2)
    _run(_create_admin(email, chosen))


@app.command("seed-demo")
def seed_demo_command() -> None:
    """Create a demo ministry year, families, children, classes, sessions, and attendance."""
    _run(_seed_demo())


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the exit code instead of raising ``SystemExit``."""
    try:
        app(args=None if argv is None else list(argv))
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
