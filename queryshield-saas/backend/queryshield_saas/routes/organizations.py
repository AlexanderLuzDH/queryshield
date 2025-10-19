from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from queryshield_saas.database import get_db
from queryshield_saas.schemas import OrganizationResponse

router = APIRouter()


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: str, db: Session = Depends(get_db)):
    """Get organization details"""
    # TODO: Implement
    # 1. Find organization by ID
    # 2. Check authorization
    # 3. Return organization data
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming soon")


@router.get("/{org_id}/members")
async def list_members(org_id: str, db: Session = Depends(get_db)):
    """List organization members"""
    # TODO: Implement
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming soon")


@router.post("/{org_id}/members")
async def add_member(org_id: str, db: Session = Depends(get_db)):
    """Add member to organization"""
    # TODO: Implement
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming soon")
