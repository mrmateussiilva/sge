from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_user
import crud
import schemas
from database import get_db
import app_cache as cache


router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=schemas.DashboardResponse)
def obter_dashboard(db: Session = Depends(get_db)) -> schemas.DashboardResponse:
    cached_data = cache.get_cached("dashboard")
    if cached_data is not None:
        return cached_data
    
    data = crud.get_dashboard_data(db)
    cache.set_cached("dashboard", data)
    return data
