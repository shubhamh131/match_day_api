from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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


@app.post("/teams")
@app.post("/teams", status_code=201)
def create_team(team: TeamCreate):
    global next_id
    new_team = {"id": next_id, **team.model_dump()}
    teams.append(new_team)
    next_id += 1
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
