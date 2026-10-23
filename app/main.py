from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import Team

app = FastAPI()
teams: list[dict] = []
next_id = 1

# @app.get("/")
# def root():
#     print("welcome to the site")


@app.get("/health")
def health():
    return {"status": "ok"}


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


def find_team(team_id: int, db: Session = Depends(get_db)) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="team not found")
    return team


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
