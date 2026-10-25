import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.football_client import (
    FootballAPIError,
    fetch_fixtures,
    fetch_scorers,
    fetch_standings,
    to_fixture,
    to_scorer,
    to_standing,
)
from app.logging_config import setup_logging
from app.models import Base, Team

setup_logging()
logger = logging.getLogger("football_fixture")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    logger.info("database tables ready")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://matchdayapi-frontend.vercel.app/",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.0f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ---------- schemas ----------


class TeamCreate(BaseModel):
    name: str = Field(min_length=1)
    external_team_id: int = Field(gt=0)
    notes: str | None = None


class TeamUpdate(BaseModel):
    notes: str | None = None


class TeamRead(BaseModel):
    id: int
    name: str
    external_team_id: int
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FixtureRead(BaseModel):
    match_id: int
    date: datetime
    competition: str
    status: str
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None


class StandingRead(BaseModel):
    position: int
    team: str
    played: int
    won: int
    draw: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int


class ScorerRead(BaseModel):
    player: str
    team: str
    goals: int
    played: int
    assists: int | None
    penalties: int | None


# ---------- helpers ----------


def find_team(team_id: int, db: Session) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


# ---------- routes ----------


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/teams", status_code=201, response_model=TeamRead)
def create_team(team: TeamCreate, db: Session = Depends(get_db)):
    new_team = Team(**team.model_dump())
    db.add(new_team)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Team already followed")
    db.refresh(new_team)
    return new_team


@app.get("/teams", response_model=list[TeamRead])
def list_teams(db: Session = Depends(get_db)):
    return db.scalars(select(Team).order_by(Team.id)).all()


@app.get("/teams/{team_id}", response_model=TeamRead)
def get_team(team_id: int, db: Session = Depends(get_db)):
    return find_team(team_id, db)


@app.patch("/teams/{team_id}", response_model=TeamRead)
def update_team(team_id: int, update: TeamUpdate, db: Session = Depends(get_db)):
    team = find_team(team_id, db)
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    db.commit()
    db.refresh(team)
    return team


@app.delete("/teams/{team_id}", status_code=204)
def delete_team(team_id: int, db: Session = Depends(get_db)):
    team = find_team(team_id, db)
    db.delete(team)
    db.commit()


@app.get("/teams/{team_id}/fixtures", response_model=list[FixtureRead])
async def get_fixtures(team_id: int, db: Session = Depends(get_db)):
    team = find_team(team_id, db)
    matches = await fetch_fixtures(team.external_team_id)
    return [to_fixture(m) for m in matches]


@app.get("/competitions/ucl/standings", response_model=list[StandingRead])
async def get_ucl_standings(limit: int = Query(20, ge=1, le=36)):
    table = await fetch_standings("CL")
    return [to_standing(row) for row in table[:limit]]


@app.get("/competitions/ucl/scorers", response_model=list[ScorerRead])
async def get_ucl_scorers(limit: int = Query(10, ge=1, le=20)):
    scorers = await fetch_scorers("CL", limit)
    return [to_scorer(s) for s in scorers]


# ---------- error handlers ----------


@app.exception_handler(FootballAPIError)
async def football_api_error_handler(request: Request, exc: FootballAPIError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
