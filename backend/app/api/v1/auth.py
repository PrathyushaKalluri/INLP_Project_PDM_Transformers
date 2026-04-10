from fastapi import APIRouter, Depends
import time
import logging

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import LoginRequest, RefreshRequest, TokenResponse, UserCreate, UserResponse
from app.services.auth import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserCreate):
    svc = AuthService()
    user = await svc.register(data)
    return user


@router.post("/login")
async def login(data: LoginRequest):
    """Login endpoint - returns tokens and user data in single response"""
    start_time = time.time()
    logger.info(f"[LOGIN] Request started for email: {data.email}")
    
    from app.schemas.user import LoginResponse
    svc = AuthService()
    
    try:
        result = await svc.login(data.email, data.password)
        elapsed = time.time() - start_time
        logger.info(f"[LOGIN] Success for {data.email} - {elapsed:.3f}s")
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[LOGIN] Failed for {data.email} - {elapsed:.3f}s - Error: {str(e)}")
        raise


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest):
    svc = AuthService()
    return await svc.refresh(data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/seed-demo-data")
async def seed_demo_data():
    """
    Create demo users, workspace, and teams for testing.
    WARNING: This endpoint should only be used in development!
    """
    from app.core.security import hash_password
    from app.repositories.user import UserRepository, WorkspaceRepository, TeamRepository
    from app.models.user import WorkspaceMember, WorkspaceRole, TeamRole
    import re
    
    try:
        # Create test users
        test_users = []
        for i, (email, name) in enumerate([
            ("alice@example.com", "Alice Johnson"),
            ("bob@example.com", "Bob Smith"),
            ("charlie@example.com", "Charlie Brown"),
            ("diana@example.com", "Diana Prince"),
        ]):
            existing = await UserRepository.get_by_email(email)
            if existing:
                test_users.append(existing)
                continue
            
            user = await UserRepository.create(
                email=email,
                hashed_password=hash_password("password123"),
                full_name=name,
                role="member",
            )
            test_users.append(user)
        
        # Create personal workspace for each user
        for user in test_users:
            slug = re.sub(r"[^a-z0-9\-]", "", user.full_name.lower().replace(" ", "-"))
            existing_personal = await WorkspaceRepository.get_by_slug(slug)
            if not existing_personal:
                await WorkspaceRepository.create(
                    name=f"{user.full_name}'s Workspace",
                    slug=slug,
                    created_by=user.id,
                    members=[WorkspaceMember(user_id=user.id, role=WorkspaceRole.ADMIN)]
                )
        
        # Create shared demo workspace for collaboration
        alice = test_users[0]
        existing_ws = await WorkspaceRepository.get_by_slug("demo-workspace")
        if not existing_ws:
            workspace = await WorkspaceRepository.create(
                name="Demo Workspace",
                slug="demo-workspace",
                created_by=alice.id,
                members=[WorkspaceMember(user_id=alice.id, role=WorkspaceRole.ADMIN)]
            )
        else:
            workspace = existing_ws
        
        # Create teams in shared workspace
        team_names = ["Frontend Team", "Backend Team"]
        for team_name in team_names:
            existing_teams = await TeamRepository.list_for_workspace(workspace.id)
            existing_team = next((t for t in existing_teams if t.name == team_name), None)
            
            if not existing_team:
                await TeamRepository.create(
                    workspace_id=workspace.id,
                    name=team_name,
                    created_by=alice.id,
                    members=[]
                )
        
        return {
            "success": True,
            "message": f"Created {len(test_users)} test users, {len(test_users)} personal workspaces, and 2 shared teams",
            "users": [{"id": str(u.id), "email": u.email, "name": u.full_name} for u in test_users],
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error seeding data: {str(e)}",
            "error": str(e)
        }
