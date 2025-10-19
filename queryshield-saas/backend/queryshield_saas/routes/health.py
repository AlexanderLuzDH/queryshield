from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from queryshield_saas.config import settings
from queryshield_saas.database import get_db
from queryshield_saas.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        database=db_status,
    )


@router.get("/ready")
async def ready_check(db: Session = Depends(get_db)):
    """Readiness check for Kubernetes/orchestration"""
    try:
        db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        return {"ready": False, "error": "Database not available"}
