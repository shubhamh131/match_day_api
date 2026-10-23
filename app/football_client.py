import httpx

from app.config import settings


async def fetch_fixtures(external_team_id: int, limit: int = 5) -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{settings.football_api_base_url}/teams/{external_team_id}/matches",
            headers={"X-Auth-Token": settings.football_api_key},
            params={"status": "SCHEDULED", "limit": limit},
        )
    response.raise_for_status()
    return response.json()["matches"]


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
