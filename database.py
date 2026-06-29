from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from settings import settings

# ساخت موتور اتصال به دیتابیس
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# ساخت نشست (Session) برای کار با دیتابیس
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# تابع سازنده برای استفاده در FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session