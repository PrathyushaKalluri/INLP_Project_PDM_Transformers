from fastapi import APIRouter

from app.api.v1 import auth, users, teams, projects, meetings, tasks

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(teams.router)
router.include_router(projects.router)
router.include_router(meetings.router)
router.include_router(tasks.router)
