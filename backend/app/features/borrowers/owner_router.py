"""Owner borrower directory endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.borrowers.models import Borrower
from app.features.owner_identity.dependencies import get_current_owner
from app.features.owner_identity.models import OwnerUser
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

router = APIRouter(prefix="/owner/borrowers", tags=["owner-borrowers"])


class OwnerBorrowerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: UUID
    first_name: str
    last_name: str
    national_id: str
    phone_number: str
    status: str


@router.get("", response_model=list[OwnerBorrowerResponse])
async def list_borrowers(
    _owner: Annotated[OwnerUser, Depends(get_current_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(None, max_length=100),
) -> list[OwnerBorrowerResponse]:
    stmt = select(Borrower).where(Borrower.status != "deleted").order_by(Borrower.last_name, Borrower.first_name)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            Borrower.first_name.ilike(term)
            | Borrower.last_name.ilike(term)
            | Borrower.national_id.ilike(term)
            | Borrower.phone_number.ilike(term)
        )
    result = await db.execute(stmt)
    borrowers = result.scalars().all()
    return [OwnerBorrowerResponse.model_validate(item) for item in borrowers]
