from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from datetime import datetime
import os

Base = declarative_base()


class Author(Base):
    """Author model"""
    __tablename__ = "authors"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    books = relationship("Book", back_populates="author", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Author(id={self.id}, name={self.name})>"


class Book(Base):
    """Book model"""
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False, index=True)
    isbn = Column(String(20), unique=True, nullable=True)
    pages = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    author = relationship("Author", back_populates="books")
    
    def __repr__(self):
        return f"<Book(id={self.id}, title={self.title})>"


def get_engine():
    """Get SQLAlchemy engine"""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost/queryshield_sample"
    )
    return create_engine(db_url, echo=False)


def init_db():
    """Initialize database"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_db():
    """Get database session dependency"""
    engine = get_engine()
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
