"""
Database configuration and session management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from config import settings

# Create async engine
# Convert to asyncpg format and use 127.0.0.1
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
DATABASE_URL = DATABASE_URL.replace("localhost", "127.0.0.1")

print(f"🔗 Database URL configured")

# For local PostgreSQL, disable SSL
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
    connect_args={
        "ssl": False,
        "timeout": 30,
        "command_timeout": 30,
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()

# Dependency to get DB session
async def get_db():
    """
    Dependency function to get database session
    Usage: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """
    Initialize database - Create all tables
    Call this on startup
    """
    async with engine.begin() as conn:
        # Import all models here to ensure they're registered
        from models.user import User
        from models.subscription import SubscriptionPlan, UserSubscription
        
        print("🗄️  Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully!")

async def close_db():
    """
    Close database connections
    Call this on shutdown
    """
    await engine.dispose()
    print("🔒 Database connections closed") 