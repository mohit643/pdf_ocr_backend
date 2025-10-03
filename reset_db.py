from database import engine
from models import Base

print("Dropping tables...")
Base.metadata.drop_all(bind=engine)

print("Creating tables...")
Base.metadata.create_all(bind=engine)

print("✅ Database reset successfully")
