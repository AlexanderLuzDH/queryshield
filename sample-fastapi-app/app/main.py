"""QueryShield FastAPI Sample Application

Demonstrates N+1 query problems and optimized solutions.

Run with:
    uvicorn app.main:app --reload

Or with QueryShield probe:
    pytest tests/ -p queryshield_sqlalchemy.runners.pytest_plugin \\
        --queryshield-engine "postgresql://..." \\
        --queryshield-report ".queryshield/report.json"
"""

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, joinedload
from typing import List
from pydantic import BaseModel

from app.models import Author, Book, init_db, get_db, get_engine

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(title="QueryShield Sample - FastAPI + SQLAlchemy")


# Pydantic schemas
class AuthorSchema(BaseModel):
    id: int
    name: str
    email: str
    
    class Config:
        from_attributes = True


class BookSchema(BaseModel):
    id: int
    title: str
    author: AuthorSchema
    
    class Config:
        from_attributes = True


# ❌ PROBLEMATIC ENDPOINT: N+1 Query Pattern
@app.get("/books-nplus1", response_model=List[BookSchema])
def get_books_with_nplus1(db: Session = Depends(get_db)):
    """
    PROBLEMATIC: Demonstrates N+1 query pattern.
    
    - First query: SELECT * FROM books (1 query)
    - Loop: For each book, SELECT * FROM authors (N queries)
    - Total: 1 + N queries = N+1 problem
    
    With 100 books, this runs 101 queries instead of 1!
    QueryShield will detect this pattern.
    """
    books = db.query(Book).all()
    
    # This loop causes N+1: each access to book.author triggers a query
    result = []
    for book in books:
        result.append({
            "id": book.id,
            "title": book.title,
            "author": {
                "id": book.author.id,
                "name": book.author.name,
                "email": book.author.email,
            }
        })
    
    return result


# ✅ OPTIMIZED ENDPOINT: Using joinedload()
@app.get("/books-optimized", response_model=List[BookSchema])
def get_books_optimized(db: Session = Depends(get_db)):
    """
    OPTIMIZED: Uses joinedload() for eager loading.
    
    - Single query with JOIN: SELECT books.*, authors.* FROM books JOIN authors
    - Fetches all data in one query
    - Total: 1 query
    
    This is 100x faster than the N+1 version!
    """
    books = db.query(Book).options(joinedload(Book.author)).all()
    
    result = []
    for book in books:
        result.append({
            "id": book.id,
            "title": book.title,
            "author": {
                "id": book.author.id,
                "name": book.author.name,
                "email": book.author.email,
            }
        })
    
    return result


# ✅ ALTERNATIVE OPTIMIZED: Using select() with joinedload()
@app.get("/books-modern", response_model=List[BookSchema])
def get_books_modern(db: Session = Depends(get_db)):
    """
    MODERN SQLALCHEMY 2.0: Using select() API.
    
    Shows the newer SQLAlchemy 2.0 style API which is more explicit.
    """
    stmt = select(Book).options(joinedload(Book.author))
    books = db.scalars(stmt).unique().all()
    
    result = []
    for book in books:
        result.append({
            "id": book.id,
            "title": book.title,
            "author": {
                "id": book.author.id,
                "name": book.author.name,
                "email": book.author.email,
            }
        })
    
    return result


# ✅ BULK LOAD: Fetch separately, then manually load relationships
@app.get("/books-bulk", response_model=List[BookSchema])
def get_books_bulk(db: Session = Depends(get_db)):
    """
    BULK LOAD: Fetch all books, then fetch all authors in bulk.
    
    - Query 1: SELECT * FROM books
    - Query 2: SELECT * FROM authors WHERE id IN (...)
    - Total: 2 queries (compared to N+1)
    
    Useful when you want to process books and authors separately.
    """
    books = db.query(Book).all()
    
    # Fetch all authors referenced by these books
    author_ids = [b.author_id for b in books]
    if author_ids:
        authors = db.query(Author).filter(Author.id.in_(author_ids)).all()
    
    # Now build result without triggering additional queries
    result = []
    for book in books:
        result.append({
            "id": book.id,
            "title": book.title,
            "author": {
                "id": book.author.id,
                "name": book.author.name,
                "email": book.author.email,
            }
        })
    
    return result


# Health check
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Root
@app.get("/")
def root():
    """Root endpoint with API overview"""
    return {
        "name": "QueryShield Sample - FastAPI + SQLAlchemy",
        "version": "0.2.0",
        "endpoints": {
            "nplus1": {
                "url": "/books-nplus1",
                "description": "N+1 query problem (DON'T USE IN PRODUCTION)",
                "queries": "N+1 (101 queries for 100 books)"
            },
            "optimized": {
                "url": "/books-optimized",
                "description": "Optimized with joinedload()",
                "queries": "1 (single join query)"
            },
            "modern": {
                "url": "/books-modern",
                "description": "SQLAlchemy 2.0 style with select()",
                "queries": "1 (single join query)"
            },
            "bulk": {
                "url": "/books-bulk",
                "description": "Bulk loading approach",
                "queries": "2 (books + authors)"
            }
        },
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
