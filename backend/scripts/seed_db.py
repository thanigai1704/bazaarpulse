#!/usr/bin/env python
"""Load the generated seed dataset into the database.

Usage:
    python scripts/seed_db.py [--path data/seed_products.json] [--reset]

    --reset   wipe existing products (and their history/reviews) first.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.services.seeder import seed_from_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Load BazaarPulse seed data.")
    parser.add_argument("--path", default=None, help="Path to seed JSON.")
    parser.add_argument("--reset", action="store_true", help="Drop + recreate tables.")
    args = parser.parse_args()

    if args.reset:
        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables.")

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        n = seed_from_json(db, args.path)
        print(f"Seeded {n} products. Ready to launch: uvicorn app.main:app")
    finally:
        db.close()


if __name__ == "__main__":
    main()
