from beanie import PydanticObjectId
import asyncio
import re
import time
import logging

from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user import AuthUserView, UserRepository
from app.schemas.user import UserCreate, TokenResponse
from app.services.errors import bad_request, conflict, not_found
from jose import JWTError

logger = logging.getLogger(__name__)


async def _create_default_workspace_and_team(user: User):
    """Create default workspace and team for new user (non-blocking)"""
    try:
        from app.services.team import WorkspaceService, TeamService
        from app.schemas.team import WorkspaceCreate, TeamCreate
        
        # Generate slug from user's name (e.g., "John Doe" -> "john-doe")
        slug = re.sub(r"[^a-z0-9\-]", "", user.full_name.lower().replace(" ", "-"))
        if not slug:
            slug = f"workspace-{str(user.id)[:12]}"
        
        ws_svc = WorkspaceService()
        workspace = await ws_svc.create(
            WorkspaceCreate(
                name=f"{user.full_name}'s Workspace",
                slug=slug
            ),
            user.id
        )
        
        team_svc = TeamService()
        await team_svc.create(
            str(workspace.id),
            TeamCreate(name=f"{user.full_name}'s Team"),
            user.id
        )
    except Exception as e:
        # Log but don't fail - workspace/team is optional
        print(f"Warning: Failed to create personal workspace/team for user {user.id}: {e}")


class AuthService:
    async def register(self, data: UserCreate) -> User:
        existing = await UserRepository.get_by_email(data.email)
        if existing:
            raise conflict("A user with this email already exists.")
        
        user = await UserRepository.create(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
        )
        
        # Create workspace/team in background (non-blocking)
        # This way, signup returns immediately
        asyncio.create_task(_create_default_workspace_and_team(user))
        
        return user

    async def login(self, email: str, password: str):
        """Login and return both tokens and user data in one response"""
        from app.schemas.user import LoginResponse
        
        start_time = time.time()
        logger.info(f"[AUTH_SERVICE] Login start for {email}")
        
        # Step 1: Fetch user from database
        db_start = time.time()
        user = await UserRepository.get_auth_view_by_email(email)
        db_time = time.time() - db_start
        logger.info(f"[AUTH_SERVICE] DB get_by_email completed - {db_time:.3f}s")
        
        if not user:
            logger.warning(f"[AUTH_SERVICE] User not found: {email}")
            raise bad_request("Invalid email or password.")
        
        # Step 2: Verify password
        verify_start = time.time()
        # bcrypt verification is CPU-bound, so run it off the event loop.
        is_valid = await asyncio.to_thread(verify_password, password, user.hashed_password)
        verify_time = time.time() - verify_start
        logger.info(f"[AUTH_SERVICE] Password verification - {verify_time:.3f}s - Valid: {is_valid}")
        
        if not is_valid:
            logger.warning(f"[AUTH_SERVICE] Invalid password for {email}")
            raise bad_request("Invalid email or password.")
        
        if not user.is_active:
            logger.warning(f"[AUTH_SERVICE] User deactivated: {email}")
            raise bad_request("Account is deactivated.")
        
        # Step 3: Create tokens
        token_start = time.time()
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        token_time = time.time() - token_start
        logger.info(f"[AUTH_SERVICE] Token generation - {token_time:.3f}s")
        
        # Step 4: Build response
        total_time = time.time() - start_time
        logger.info(f"[AUTH_SERVICE] Login complete for {email} - Total: {total_time:.3f}s (DB: {db_time:.3f}s, Verify: {verify_time:.3f}s, Token: {token_time:.3f}s)")
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user if isinstance(user, User) else AuthUserView.model_validate(user),
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
