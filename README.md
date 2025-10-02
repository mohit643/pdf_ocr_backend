# 📝 PDF Editor with Database - Complete Guide

## 🎯 Project Overview

Ye ek complete PDF editor application hai jo PDFs ko upload karke edit kar sakta hai aur har change ko database mein store karta hai. **1000+ PDFs easily handle kar sakta hai** with proper indexing and pagination.

### ✨ Key Features

- ✅ **PDF Upload & Storage** - Database mein complete metadata save
- ✅ **Text Editing** - Direct text modification with visual interface
- ✅ **Version Control** - Har edit ka alag version save
- ✅ **Search & Filter** - Filename se PDFs search karo
- ✅ **Activity Logs** - Har action track karo
- ✅ **Statistics** - Storage, files count, versions
- ✅ **Scalable** - 1000+ PDFs ke liye optimized
- ✅ **Production Ready** - Proper error handling, logging

---

## 📁 Complete File Structure

```
pdf-editor/
│
├── backend/
│   ├── app.py                  # Main FastAPI application (460 lines)
│   ├── models.py               # SQLAlchemy database models (150 lines)
│   ├── database.py             # Database configuration (60 lines)
│   ├── crud.py                 # CRUD operations (250 lines)
│   ├── schemas.py              # Pydantic validation schemas (100 lines)
│   ├── config.py               # Configuration settings (80 lines)
│   ├── test_db.py              # Database testing script (150 lines)
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # Environment variables (create this)
│   ├── start.sh                # Linux/Mac quick start
│   ├── start.bat               # Windows quick start
│   ├── uploads/                # Original PDFs (auto-created)
│   ├── outputs/                # Edited PDFs (auto-created)
│   └── thumbnails/             # Page thumbnails (auto-created)
│
└── frontend/
    ├── src/
    │   └── App.jsx             # React application
    ├── package.json
    └── public/
```

---

## 🚀 Quick Start (3 Steps)

### Step 1: Database Setup

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Create database
sudo -u postgres psql
CREATE DATABASE pdf_editor;
\q
```

### Step 2: Backend Setup

```bash
# Navigate to backend
cd backend

# Create & activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/pdf_editor
REDIS_HOST=localhost
REDIS_PORT=6379
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
THUMBNAIL_DIR=thumbnails
SECRET_KEY=change-this-in-production
HOST=0.0.0.0
PORT=8000
EOF

# Test database connection
python test_db.py

# Start backend
python app.py
```

### Step 3: Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start frontend
npm start
```

**🎉 Done! Open http://localhost:3000**

---

## 🗄️ Database Schema Explained

### 1. **pdfs** table (Main PDFs)

```sql
- id: Primary key
- user_id: Optional user reference
- original_filename: "report.pdf"
- stored_filename: "20241001_abc123_report.pdf"
- file_path: "/uploads/20241001_abc123_report.pdf"
- file_size: 2048576 (bytes)
- total_pages: 10
- session_id: "unique-session-id"
- status: "uploaded", "ready", "processing"
- is_active: true/false (soft delete)
- uploaded_at: timestamp
- updated_at: timestamp
```

**Purpose**: Har uploaded PDF ki complete information

### 2. **pdf_versions** table (Edited Versions)

```sql
- id: Primary key
- original_pdf_id: Reference to pdfs table
- version_number: 1, 2, 3...
- version_name: "Version 1", "Final Draft"
- stored_filename: "edited_20241001_report.pdf"
- file_path: "/outputs/edited_20241001_report.pdf"
- file_size: 2100000 (bytes)
- total_edits: 5
- edit_summary: JSON of all edits
- created_at: timestamp
```

**Purpose**: Har edit ka alag version save, rollback possible

### 3. **pdf_pages** table (Page Data)

```sql
- id: Primary key
- pdf_id: Reference to pdfs table
- page_number: 0, 1, 2... (0-indexed)
- width: 800 (pixels)
- height: 1000 (pixels)
- thumbnail_path: "/thumbnails/session_page_0.png"
- text_blocks: JSON array of text with positions
- created_at: timestamp
```

**Purpose**: Har page ka data separately, fast retrieval

### 4. **pdf_edits** table (Individual Edits)

```sql
- id: Primary key
- version_id: Reference to pdf_versions table
- page_number: 0, 1, 2...
- bbox: "100,200,300,250" (x0,y0,x1,y1)
- old_text: "Original text"
- new_text: "Modified text"
- font_size: 12
- color: "#000000"
- created_at: timestamp
```

**Purpose**: Har individual edit ki detailed history

### 5. **activity_logs** table (Tracking)

```sql
- id: Primary key
- user_id: Optional user reference
- pdf_id: Reference to pdfs table
- action: "upload", "edit", "download", "delete"
- details: JSON with additional info
- ip_address: "192.168.1.1"
- created_at: timestamp
```

**Purpose**: Audit trail, security, analytics

### 6. **users** table (Optional)

```sql
- id: Primary key
- email: "user@example.com"
- name: "User Name"
- created_at: timestamp
```

**Purpose**: User management (if authentication added)

---

## 🔧 API Endpoints

### Upload & Download

```http
POST /api/upload
  - Upload PDF file
  - Returns: session_id, pdf_id, pages data

POST /api/download
  - Body: {session_id, edits: [...]}
  - Returns: Edited PDF file
```

### PDF Management

```http
GET /api/pdfs
  - List all PDFs (paginated)
  - Query params: skip=0, limit=100

GET /api/pdfs/{id}
  - Get specific PDF details

GET /api/pdfs/{id}/versions
  - Get all versions of a PDF

GET /api/pdfs/{id}/pages
  - Get all pages with text blocks

DELETE /api/pdfs/{id}
  - Soft delete PDF
```

### Search & Stats

```http
GET /api/search?q=filename
  - Search PDFs by filename

GET /api/stats
  - Get statistics (total PDFs, storage, etc.)

GET /api/activity
  - Get activity logs
  - Query params: pdf_id, limit

GET /api/health
  - Health check
```

---

## 💡 How It Works

### 1. **Upload Flow**

```
User uploads PDF → FastAPI receives file → Saves to uploads/
→ Extracts text blocks → Renders thumbnails → Saves to database
→ Creates pdf_pages records → Returns session_id + page data
```

### 2. **Edit Flow**

```
User enables edit mode → Clicks text → Modifies content
→ Frontend tracks changes → Stores in edits array
→ User clicks download → Sends edits to backend
```

### 3. **Download Flow**

```
Backend receives edits → Loads original PDF from database
→ Applies all text edits → Generates new PDF → Saves as version
→ Creates pdf_versions record → Saves individual pdf_edits
→ Logs activity → Returns file to user
```

### 4. **Database Storage**

```
All metadata in PostgreSQL → Actual PDF files in filesystem
→ Thumbnails cached separately → Text blocks as JSON
→ Fast queries with proper indexing
```

---

## 🔍 Testing

### Test Database Connection

```bash
cd backend
python test_db.py
```

### Test API Endpoints

```bash
# Open API docs
http://localhost:8000/docs

# Or use curl
curl http://localhost:8000/api/health
curl http://localhost:8000/api/stats
```

### Test Upload

1. Open http://localhost:3000
2. Upload any PDF
3. Check terminal for logs
4. Verify database:

```bash
sudo -u postgres psql pdf_editor
SELECT * FROM pdfs;
SELECT * FROM pdf_pages;
\q
```

---

## 📊 Scalability for 1000+ PDFs

### Database Optimizations

✅ **Indexes** on commonly queried fields:

- `session_id` (unique index)
- `uploaded_at` (for sorting)
- `original_filename` (for search)
- `user_id` (if using authentication)

✅ **Pagination** implemented:

- Default limit: 100 records per page
- Use `skip` and `limit` parameters

✅ **Connection Pooling**:

- Pool size: 20 connections
- Max overflow: 40 connections
- Connection recycling: 1 hour

✅ **Soft Deletes**:

- Files never physically deleted initially
- `is_active` flag for filtering
- Can implement cleanup cron job

### File Storage Optimizations

✅ **Organized Structure**:

```
uploads/
├── 20241001_abc123_file1.pdf
├── 20241001_def456_file2.pdf
└── ...

outputs/
├── edited_20241001_file1.pdf
├── edited_20241002_file1.pdf
└── ...

thumbnails/
├── abc123_page_0.png
├── abc123_page_1.png
└── ...
```

✅ **Recommended for Large Scale**:

- Use cloud storage (AWS S3, Google Cloud Storage)
- Implement CDN for thumbnails
- Compress old files
- Archive old versions

### Performance Tips

```python
# Good - Uses pagination
pdfs = crud.get_all_pdfs(db, skip=0, limit=100)

# Bad - Loads everything
pdfs = db.query(PDF).all()  # Don't do this!

# Good - Indexed search
results = crud.search_pdfs(db, "report")

# Good - Specific fields only
db.query(PDF.id, PDF.filename).filter(...)
```

---

## 🔒 Security Recommendations

### For Production:

1. **Change SECRET_KEY** in .env
2. **Add authentication** (JWT tokens)
3. **Enable HTTPS** (SSL certificates)
4. **Input validation** (file size, type)
5. **Rate limiting** (max uploads per hour)
6. **SQL injection protection** (already handled by SQLAlchemy)
7. **File upload limits** (already set to 50MB)
8. **CORS** properly configured

---

## 🛠️ Troubleshooting

### Database Connection Failed

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check if database exists
sudo -u postgres psql -l | grep pdf_editor

# Check .env file
cat backend/.env
```

### Import Errors

```bash
# Make sure you're in virtual environment
which python  # Should show venv path

# Reinstall dependencies
pip install -r requirements.txt
```

### Port Already in Use

```bash
# Kill process on port 8000
sudo lsof -ti:8000 | xargs kill -9

# Or change port in .env
PORT=8001
```

### Permission Denied (uploads/)

```bash
chmod -R 755 backend/uploads backend/outputs backend/thumbnails
```

---

## 📝 Next Steps

### Immediate:

- [ ] Test with your own PDFs
- [ ] Verify all database operations
- [ ] Check file uploads work

### Short-term:

- [ ] Add user authentication
- [ ] Implement file compression
- [ ] Add PDF preview feature
- [ ] Create cleanup script for old files

### Long-term:

- [ ] Move to cloud storage (S3)
- [ ] Add collaborative editing
- [ ] Implement real-time notifications
- [ ] Create admin dashboard
- [ ] Add PDF annotations
- [ ] Support for images and signatures

---

## 📞 Support

**Check logs for detailed errors:**

- Backend logs in terminal
- Frontend logs in browser console
- Database logs: `sudo journalctl -u postgresql`

**Common Issues:**

- Database connection → Check .env DATABASE_URL
- File upload fails → Check folder permissions
- API errors → Check http://localhost:8000/docs

---

## ✅ Success Checklist

- [x] PostgreSQL installed and running
- [x] Database `pdf_editor` created
- [x] Backend dependencies installed
- [x] Frontend dependencies installed
- [x] .env file configured
- [x] Database tables created
- [x] Backend running on port 8000
- [x] Frontend running on port 3000
- [x] Can upload PDF
- [x] Can edit text
- [x] Can download edited PDF
- [x] Data saved in database

**Congratulations! Aapka PDF Editor with Database ready hai! 🎉**
