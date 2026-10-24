import logging

import httpx

from app.config import settings

logger = logging.getLogger("football_fixture")


class FootballAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


async def _get(path: str, params: dict | None = None) -> dict:
    url = f"{settings.football_api_base_url}{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={"X-Auth-Token": settings.football_api_key},
                params=params,
            )
        response.raise_for_status()
    except httpx.TimeoutException:
        logger.error("football-data.org timed out for %s", path)
        raise FootballAPIError(504, "Football data provider timed out")
    except httpx.HTTPStatusError as exc:
        upstream = exc.response.status_code
        logger.error("football-data.org returned %s for %s", upstream, path)
        if upstream == 429:
            raise FootballAPIError(
                503, "Football data provider rate limit reached, try again later"
            )
        raise FootballAPIError(502, "Football data provider returned an error")
    except httpx.RequestError:
        logger.error("could not reach football-data.org for %s", path)
        raise FootballAPIError(502, "Could not reach football data provider")
    return response.json()


async def fetch_fixtures(external_team_id: int, limit: int = 5) -> list[dict]:
    data = await _get(
        f"/teams/{external_team_id}/matches",
        {"status": "SCHEDULED", "limit": limit},
    )
    matches = data["matches"]
    logger.info(
        "football-data.org returned %d matches for team %s",
        len(matches),
        external_team_id,
    )
    return matches


async def fetch_standings(competition: str = "CL") -> list[dict]:
    data = await _get(f"/competitions/{competition}/standings")
    return data["standings"][0]["table"]


async def fetch_scorers(competition: str = "CL", limit: int = 10) -> list[dict]:
    data = await _get(f"/competitions/{competition}/scorers", {"limit": limit})
    return data["scorers"]


def to_fixture(match: dict) -> dict:
    return {
        "match_id": match["id"],
        "date": match["utcDate"],
        "competition": match["competition"]["name"],
        "status": match["status"],
        "home_team": match["homeTeam"]["name"],
        "away_team": match["awayTeam"]["name"],
        "home_score": match["score"]["fullTime"]["home"],
        "away_score": match["score"]["fullTime"]["away"],
    }


def to_standing(row: dict) -> dict:
    return {
        "position": row["position"],
        "team": row["team"]["name"],
        "played": row["playedGames"],
        "won": row["won"],
        "draw": row["draw"],
        "lost": row["lost"],
        "goals_for": row["goalsFor"],
        "goals_against": row["goalsAgainst"],
        "goal_difference": row["goalDifference"],
        "points": row["points"],
    }
