import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from backend.database import get_db
from backend.services.curriculum import build_todays_plan

router = APIRouter(prefix="/api", tags=["progress"])


@router.get("/today")
async def get_today(db: sqlite3.Connection = Depends(get_db)) -> dict:
    return build_todays_plan(db)


@router.get("/panel")
async def get_panel() -> None:
    raise HTTPException(status_code=501, detail="Panel de apoyo: pendiente de ITER-4")


@router.get("/progress")
async def get_progress() -> None:
    raise HTTPException(
        status_code=501, detail="Dashboard de progreso: pendiente de ITER-5"
    )


@router.get("/stats")
async def get_stats() -> None:
    raise HTTPException(status_code=501, detail="Stats: pendiente de ITER-5")
