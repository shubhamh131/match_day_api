# Matchday API

A REST API for following football teams. Save the teams you care about, then ask the API for their upcoming fixtures, plus the Champions League table and top scorers. Fixture data comes live from [football-data.org](https://www.football-data.org/).

Built as a "no-AI" backend service: the running product has no LLM or AI dependency. It uses Python, FastAPI, PostgreSQL, and Docker.

## What it does

- Follow a team, list followed teams, edit its notes, and unfollow it (full CRUD, stored in PostgreSQL).
- Get a followed team's upcoming fixtures from football-data.org (async call).
- Get the UEFA Champions League league table and top scorers.
- Return clear errors for bad input, missing teams, duplicates and upstream failures.

One stored row looks like this:

```
id=1 | name="FC Barcelona" | external_team_id=81 | notes="Watch every El Clasico"
```

`id` is our own database id. `external_team_id` is the team's id in football-data.org, used when calling their API.

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.13 |
| Web framework | FastAPI (served by uvicorn) |
| Validation | Pydantic v2 |
| Database | PostgreSQL 16 via SQLAlchemy 2 and psycopg |
| External API client | httpx (async) |
| Config | pydantic-settings (environment variables, `.env` locally) |
| Packaging | Docker, Docker Compose |

## Architecture

```
Browser or curl
      |
      v
FastAPI route  --validates--> Pydantic schema
      |
      +--> SQLAlchemy session --> PostgreSQL        (teams)
      |
      +--> football_client (httpx, async) --> football-data.org   (fixtures, standings, scorers)
```

Design choices:

- **Separate schemas** for input (`TeamCreate`, `TeamUpdate`) and output (`TeamRead`). The client never sets `id` or `created_at`.
- **The football-data.org code lives in one file** (`app/football_client.py`). It sets the API key header, applies a 10 second timeout, converts upstream failures into our own error type, and flattens their large JSON into small response models.
- **The database enforces uniqueness.** `external_team_id` is unique, so following the same team twice is rejected by Postgres and returned as a 409.
- **Config comes from environment variables**, so the same code runs on a laptop and in Docker with different settings.
- **Tables are created at startup**, so a brand-new database works with no manual step.

## API endpoints

| Method | Path | Purpose | Success |
|---|---|---|---|
| GET | `/health` | Health check | 200 |
| POST | `/teams` | Follow a team | 201 |
| GET | `/teams` | List followed teams | 200 |
| GET | `/teams/{id}` | Get one team | 200 |
| PATCH | `/teams/{id}` | Edit a team's notes | 200 |
| DELETE | `/teams/{id}` | Unfollow a team | 204 |
| GET | `/teams/{id}/fixtures` | Upcoming fixtures from football-data.org | 200 |
| GET | `/competitions/ucl/standings?limit=20` | Champions League table (1 to 36 rows) | 200 |
| GET | `/competitions/ucl/scorers?limit=10` | Champions League top scorers (1 to 20 rows) | 200 |

Interactive docs are served at `/docs` (Swagger UI).

### Example requests

```bash
# follow a team
curl -X POST http://127.0.0.1:8000/teams \
  -H "Content-Type: application/json" \
  -d '{"name": "FC Barcelona", "external_team_id": 81, "notes": "Watch every El Clasico"}'

# upcoming fixtures for team id 1
curl http://127.0.0.1:8000/teams/1/fixtures
```

A fixture in the response (the score is `null` until the match is played):

```json
{
  "match_id": 564723,
  "date": "2026-10-25T20:00:00Z",
  "competition": "Primera Division",
  "status": "TIMED",
  "home_team": "FC Barcelona",
  "away_team": "Real Madrid CF",
  "home_score": null,
  "away_score": null
}
```

## Error handling

| Situation | Status | Response body |
|---|---|---|
| Invalid input (empty name, `external_team_id` below 1) | 422 | Field-level details from Pydantic |
| Team id does not exist | 404 | `{"detail": "Team not found"}` |
| Team already followed | 409 | `{"detail": "Team already followed"}` |
| football-data.org times out | 504 | `{"detail": "Football data provider timed out"}` |
| football-data.org rate limit reached | 503 | `{"detail": "Football data provider rate limit reached, try again later"}` |
| football-data.org rejects the key, errors, or is unreachable | 502 | `{"detail": "Football data provider returned an error"}` |
| Anything unexpected | 500 | `{"detail": "Internal server error"}` (full traceback goes to the log only) |

## Run it locally

You need Docker and a free football-data.org API key.

```bash
git clone https://github.com/shubhamh131/match_day_api.git
cd match_day_api
cp .env.example .env        # then put your API key in .env
docker compose up -d --build
```

Open http://127.0.0.1:8000/docs.

`docker compose` starts two containers: the API and PostgreSQL 16. Inside Compose the API reaches the database at host `db`, and data is kept in a named volume (`pgdata`).

Useful commands:

```bash
docker compose logs -f app     # follow the API logs
docker compose down            # stop everything, keep the data
docker compose down -v         # stop everything and delete the database data
```

### Without Docker for the API (auto-reload)

```bash
docker compose up -d db
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes | PostgreSQL connection string. `postgres://` and `postgresql://` are converted to the psycopg driver automatically |
| `FOOTBALL_API_KEY` | yes | football-data.org API token, sent as the `X-Auth-Token` header |
| `FOOTBALL_API_BASE_URL` | no | Defaults to `https://api.football-data.org/v4` |
| `LOG_LEVEL` | no | Defaults to `INFO` |
| `CORS_ORIGINS` | no | Comma-separated list of web page origins allowed to call the API. Defaults to `http://localhost:5500,http://127.0.0.1:5500` |

Secrets live only in `.env`, which is git-ignored. `.env.example` lists the variable names.

## Logging

One log line per request (method, path, status, duration in ms), one line per football-data.org call, and a full traceback for unexpected errors. Verbosity is controlled by `LOG_LEVEL`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests run against an in-memory SQLite database, never the real Postgres. Test coverage is still small and growing.

## Dashboard (optional)

A static page in `frontend/` shows the Champions League table and top scorers from the API. With the API running locally:

```bash
cd frontend
python -m http.server 5500
```

Then open http://localhost:5500.

## Repository layout

```
app/
  main.py             routes, schemas, error handlers, middleware
  config.py           settings from environment variables
  database.py         engine and session dependency
  models.py           SQLAlchemy Team model
  football_client.py  football-data.org client and response mapping
  logging_config.py   logging setup
tests/                pytest tests
frontend/             static dashboard page (HTML, CSS, JavaScript)
Dockerfile
docker-compose.yml    API + PostgreSQL for local use
requirements.txt
requirements-dev.txt
.env.example
AI_FAILURES.md
```

## Known limitations

- **No database migrations.** Tables are created with `create_all` at startup, which only creates missing tables. Changing an existing column needs a migration tool such as Alembic.
- **Blocking database calls inside async routes.** The fixtures route is `async` for the external call, but it uses a synchronous SQLAlchemy session. Fine at this scale. Async SQLAlchemy would be the next step.
- **No caching.** Every standings, scorers or fixtures request calls football-data.org, whose free plan allows 10 requests per minute.
- **No authentication.** Anyone can create or delete teams.

## How AI tools were used

A coding assistant helped build this project. Every generated change was reviewed through its Git diff before being committed and checked with manual API calls and logs. One case where the assistant was wrong is documented in [AI_FAILURES.md](AI_FAILURES.md). The service itself has no AI component.
