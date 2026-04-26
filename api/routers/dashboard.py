from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import crud
import schemas
from database import get_db


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardResponse)
def obter_dashboard(db: Session = Depends(get_db)) -> schemas.DashboardResponse:
    return crud.get_dashboard_data(db)
