from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_authenticated_user
from app.db.session import get_db
from app.models import User
from app.schemas.settings import UserSettingsPayload, UserSettingsResponse
from app.services.user_settings_service import UserSettingsService

router = APIRouter(dependencies=[Depends(require_authenticated_user)])


@router.get("/me", response_model=UserSettingsResponse)
def get_my_settings(user: User = Depends(require_authenticated_user)) -> UserSettingsResponse:
    return UserSettingsResponse(settings=UserSettingsService.get_user_settings(user))


@router.put("/me", response_model=UserSettingsResponse)
def update_my_settings(
    payload: UserSettingsPayload,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> UserSettingsResponse:
    UserSettingsService.set_user_settings(user, payload)
    db.commit()
    db.refresh(user)
    return UserSettingsResponse(settings=UserSettingsService.get_user_settings(user))
