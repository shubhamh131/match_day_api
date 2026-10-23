from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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


@app.get("/teams")
def list_teams():
    return teams


@app.get("/teams/{team_id}")
def get_team(team_id: int):
    for team in teams:
        if team["id"] == team_id:
            return team
    raise HTTPException(status_code=404, detail="Team not found")


def find_team(team_id: int) -> dict:
    for team in teams:
        if team["id"] == team_id:
            return team
    raise HTTPException(status_code=404, detail="Team not found")


@app.get("/teams/{team_id}")
def get_team(team_id: int):
    return find_team(team_id)


@app.patch("/teams/{team_id}")
def update_team(team_id: int, update: TeamUpdate):
    team = find_team(team_id)
    team.update(update.model_dump(exclude_unset=True))
    return team


@app.delete("/teams/{team_id}", status_code=204)
def delete_team(team_id: int):
    team = find_team(team_id)
    teams.remove(team)
