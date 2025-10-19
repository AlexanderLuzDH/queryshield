"""
Test suite for QueryShield FastAPI sample application.

Run with QueryShield probe:
    pytest tests/test_nplus1.py \\
        -p queryshield_sqlalchemy.runners.pytest_plugin \\
        --queryshield-engine "postgresql://postgres:postgres@localhost/queryshield_sample" \\
        --queryshield-report ".queryshield/report.json"
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Base, Author, Book


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine"""
    # Use test database
    db_url = "postgresql://postgres:postgres@localhost/queryshield_sample_test"
    engine = create_engine(db_url)
    
    # Create tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(test_engine):
    """Create test database session"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def setup_data(session):
    """Setup test data"""
    # Create 10 authors with 10 books each
    for i in range(10):
        author = Author(name=f"Author {i}", email=f"author{i}@example.com")
        session.add(author)
        session.flush()
        
        for j in range(10):
            book = Book(
                title=f"Book {i}-{j}",
                author_id=author.id,
                pages=100 + (i * 10) + j,
            )
            session.add(book)
    
    session.commit()


# ❌ PROBLEMATIC TEST: Demonstrates N+1 problem
def test_books_nplus1_problem(session):
    """
    This test demonstrates the N+1 query problem.
    
    QueryShield will detect:
    - First query: SELECT * FROM books (1 query)
    - Then: 100 queries to fetch authors (N queries)
    - Total: 101 queries
    
    Expected to trigger N+1 alert in QueryShield report.
    """
    books = session.query(Book).all()
    assert len(books) == 100
    
    # This loop causes N+1: each access triggers a query
    for book in books:
        assert book.author.name is not None


# ✅ OPTIMIZED TEST: Using joinedload()
def test_books_optimized_query(session):
    """
    This test demonstrates the optimized query pattern.
    
    QueryShield will detect:
    - Single query with JOIN: SELECT books.*, authors.* FROM books JOIN authors
    - Total: 1 query (much better!)
    
    Expected to pass with 1 query in QueryShield report.
    """
    from sqlalchemy import joinedload
    
    books = session.query(Book).options(joinedload(Book.author)).all()
    assert len(books) == 100
    
    # Accessing author doesn't trigger additional queries
    for book in books:
        assert book.author.name is not None


# ✅ BULK LOAD TEST
def test_books_bulk_load(session):
    """
    Bulk loading approach: 2 queries instead of 101.
    
    QueryShield will show:
    - Query 1: SELECT * FROM books
    - Query 2: SELECT * FROM authors WHERE id IN (...)
    - Total: 2 queries
    """
    books = session.query(Book).all()
    
    # Fetch all authors in bulk
    author_ids = [b.author_id for b in books]
    authors_map = {a.id: a for a in session.query(Author).filter(Author.id.in_(author_ids)).all()}
    
    # Access authors from map (no additional queries)
    for book in books:
        author = authors_map.get(book.author_id)
        assert author is not None
        assert author.name is not None
