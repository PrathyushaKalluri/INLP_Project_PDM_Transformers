from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.errors import not_found
from app.repositories.user import UserRepository
from app.core.security import hash_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserResponse])
async def search_users(
    email: str = Query(default=None, description="Filter by exact email address"),
    current_user: User = Depends(get_current_user),
):
    if email:
        user = await UserRepository.get_by_email(email)
        return [user] if user else []
    return await User.find_all().to_list()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
):
    updates = {}
    if data.full_name is not None:
        updates["full_name"] = data.full_name
    if data.password is not None:
        updates["hashed_password"] = hash_password(data.password)
    await UserRepository.update(current_user, **updates)
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise not_found("User")
    return user
