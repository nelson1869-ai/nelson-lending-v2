"""Secure one-time CLI bootstrap for the business Owner."""

import argparse
import asyncio
import getpass

from app.db.session import engine, session_factory
from app.features.owner_identity.exceptions import OwnerAlreadyBootstrapped
from app.features.owner_identity.service import bootstrap_owner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the one Lending Nelson Owner")
    parser.add_argument("--username", required=True, help="Case-insensitive Owner username")
    return parser.parse_args()


async def run(username: str, password: str) -> None:
    async with session_factory() as session:
        owner = await bootstrap_owner(session, username=username, password=password)
    print(f"Owner bootstrap complete for username: {owner.username}")


async def main() -> int:
    args = parse_args()
    password = getpass.getpass("Owner password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        print("Passwords do not match")
        return 1
    try:
        await run(args.username, password)
    except (OwnerAlreadyBootstrapped, ValueError) as exc:
        print(str(exc))
        return 1
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
