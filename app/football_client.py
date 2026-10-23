import logging

import httpx

from app.config import settings

logger = logging.getLogger("football_fixture")


class FootballAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


async def fetch_fixtures(external_team_id: int, limit: int = 5) -> list[dict]:
    url = f"{settings.football_api_base_url}/teams/{external_team_id}/matches"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={"X-Auth-Token": settings.football_api_key},
                params={"status": "SCHEDULED", "limit": limit},
            )
        response.raise_for_status()
    except httpx.TimeoutException:
        logger.error("football-data.org timed out for team %s", external_team_id)
        raise FootballAPIError(504, "Fixtures provider timed out")
    except httpx.HTTPStatusError as exc:
        upstream = exc.response.status_code
        logger.error(
            "football-data.org returned %s for team %s", upstream, external_team_id
        )
        if upstream == 429:
            raise FootballAPIError(
                503, "Fixtures provider rate limit reached, try again later"
            )
        raise FootballAPIError(502, "Fixtures provider returned an error")
    except httpx.RequestError:
        logger.error("could not reach football-data.org")
        raise FootballAPIError(502, "Could not reach fixtures provider")
        matches = response.json()["matches"]
        logger.info(
            "football-data.org returned %d matches for team %s",
            len(matches),
            external_team_id,
        )
        return matches


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
