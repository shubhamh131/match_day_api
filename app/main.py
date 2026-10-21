from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


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


@app.post("/teams")
def create_team(team: TeamCreate):
    return {"id": 1, **team.model_dump()}
