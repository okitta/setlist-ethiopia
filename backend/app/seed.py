"""Seed a local/preview database with non-personal demo data.

Run: python -m app.seed
Never seed against production, and never use production user data here.
"""

from sqlalchemy import select

from app.crud import slugify
from app.database import SessionLocal
from app.models import Artist, Role, User


def seed() -> None:
    db = SessionLocal()
    try:
        users = [
            ("fan_hana", "Hana", Role.contributor),
            ("curator_sam", "Sam", Role.curator),
        ]
        for handle, name, role in users:
            if not db.scalar(select(User).where(User.handle == handle)):
                db.add(User(handle=handle, display_name=name, role=role))

        artists = ["Mahmoud Ahmed", "Aster Aweke", "Teddy Afro", "Mulatu Astatke"]
        for name in artists:
            slug = slugify(name)
            if not db.scalar(select(Artist).where(Artist.slug == slug)):
                db.add(Artist(name=name, slug=slug))

        db.commit()
        print("Seeded demo users and artists.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
