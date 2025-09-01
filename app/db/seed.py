import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import Base, engine, async_session_maker
from app.db.user import User, UserRole
from app.auth.auth import pwd_context

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")

async def seed_admin_user():
    async with async_session_maker() as session:
        admin_email = "admin@example.com"
        admin_username = "admin"
        admin_password = "adminpassword"

        existing_admin = await session.execute(
            select(User).where(User.email == admin_email)
        )
        if existing_admin.scalars().first():
            print("Admin user already exists.")
            return

        hashed_password = pwd_context.hash(admin_password)

        admin_user = User(
            username=admin_username,
            email=admin_email,
            hashed_password=hashed_password,
            first_name="Super",
            last_name="Admin",
            role=UserRole.admin,
            is_active=True,
        )
        session.add(admin_user)
        await session.commit()
        print(f"Admin user '{admin_username}' created successfully.")

async def main():
    await create_tables()
    await seed_admin_user()

if __name__ == "__main__":
    asyncio.run(main())
