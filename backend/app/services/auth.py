from beanie import PydanticObjectId

from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, TokenResponse
from app.services.errors import bad_request, conflict, not_found
from jose import JWTError


class AuthService:
    async def register(self, data: UserCreate) -> User:
        existing = await UserRepository.get_by_email(data.email)
        if existing:
            raise conflict("A user with this email already exists.")
        return await UserRepository.create(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
        )

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await UserRepository.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise bad_request("Invalid email or password.")
        if not user.is_active:
            raise bad_request("Account is deactivated.")
        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise bad_request("Invalid or expired refresh token.")
        if payload.get("type") != "refresh":
            raise bad_request("Invalid token type.")
        user_id = payload.get("sub")
        user = await UserRepository.get_by_id(user_id)
        if not user or not user.is_active:
            raise not_found("User")
        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )
