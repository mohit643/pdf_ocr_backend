"""
Database Connection Test Script
Save as: backend/test_db.py
Run: python test_db.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_database_connection():
    """Test database connection and operations"""
    print("=" * 60)
    print("🧪 Testing Database Connection")
    print("=" * 60)
    print()
    
    # Test 1: Import modules
    print("1️⃣ Testing imports...")
    try:
        from database import SessionLocal, init_db, check_db_connection
        from models import PDF, PDFVersion, PDFPage
        import crud
        print("   ✅ All modules imported successfully")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 2: Check connection
    print("\n2️⃣ Testing database connection...")
    try:
        if check_db_connection():
            print("   ✅ Database connection successful")
        else:
            print("   ❌ Database connection failed")
            return False
    except Exception as e:
        print(f"   ❌ Connection test failed: {e}")
        return False
    
    # Test 3: Initialize tables
    print("\n3️⃣ Creating/verifying database tables...")
    try:
        init_db()
        print("   ✅ Database tables ready")
    except Exception as e:
        print(f"   ❌ Table creation failed: {e}")
        return False
    
    # Test 4: Test CRUD operations
    print("\n4️⃣ Testing CRUD operations...")
    db = SessionLocal()
    try:
        # Create test PDF
        test_pdf = crud.create_pdf(
            db=db,
            original_filename="test.pdf",
            stored_filename="test_123.pdf",
            file_path="/uploads/test_123.pdf",
            file_size=1024,
            total_pages=5,
            session_id="test-session-123"
        )
        print(f"   ✅ Created test PDF (ID: {test_pdf.id})")
        
        # Retrieve PDF
        retrieved = crud.get_pdf_by_session(db, "test-session-123")
        if retrieved and retrieved.id == test_pdf.id:
            print(f"   ✅ Retrieved PDF successfully")
        else:
            print("   ❌ Failed to retrieve PDF")
            return False
        
        # Create test page
        test_page = crud.create_pdf_page(
            db=db,
            pdf_id=test_pdf.id,
            page_number=0,
            width=800,
            height=1000,
            thumbnail_path="/thumbnails/test_0.png",
            text_blocks=[{"text": "Test", "bbox": [0, 0, 100, 100]}]
        )
        print(f"   ✅ Created test page (ID: {test_page.id})")
        
        # List PDFs
        all_pdfs = crud.get_all_pdfs(db, limit=10)
        print(f"   ✅ Listed PDFs (found {len(all_pdfs)})")
        
        # Clean up test data
        crud.delete_pdf(db, test_pdf.id)
        print("   ✅ Cleaned up test data")
        
    except Exception as e:
        print(f"   ❌ CRUD operations failed: {e}")
        return False
    finally:
        db.close()
    
    # Test 5: Check statistics
    print("\n5️⃣ Testing statistics...")
    db = SessionLocal()
    try:
        from sqlalchemy import func
        total = db.query(func.count(PDF.id)).filter(PDF.is_active == True).scalar()
        print(f"   ✅ Total active PDFs: {total}")
    except Exception as e:
        print(f"   ❌ Statistics failed: {e}")
        return False
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("✅ All database tests passed!")
    print("=" * 60)
    return True

def show_database_info():
    """Show database information"""
    print("\n📊 Database Information:")
    print("-" * 60)
    
    try:
        from config import settings
        print(f"Database URL: {settings.DATABASE_URL}")
        print(f"Upload Dir:   {settings.UPLOAD_DIR}")
        print(f"Output Dir:   {settings.OUTPUT_DIR}")
        print(f"Thumbnail:    {settings.THUMBNAIL_DIR}")
    except Exception as e:
        print(f"Could not load config: {e}")
    
    print("-" * 60)

def check_tables():
    """List all database tables"""
    print("\n📋 Database Tables:")
    print("-" * 60)
    
    try:
        from database import SessionLocal
        from sqlalchemy import inspect
        
        db = SessionLocal()
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        if tables:
            for i, table in enumerate(tables, 1):
                print(f"{i}. {table}")
        else:
            print("No tables found. Run init_db() first.")
        
        db.close()
    except Exception as e:
        print(f"Error listing tables: {e}")
    
    print("-" * 60)

if __name__ == "__main__":
    print()
    show_database_info()
    check_tables()
    print()
    
    # Run tests
    success = test_database_connection()
    
    if success:
        print("\n🎉 Your database is ready to use!")
        print("\nNext steps:")
        print("1. Run: python app.py")
        print("2. Open: http://localhost:8000/docs")
        print("3. Test API endpoints")
    else:
        print("\n⚠️  Please fix the errors above and try again")
        sys.exit(1)