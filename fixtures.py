import os
import requests
from datetime import datetime


API_URL = "https://v3.football.api-sports.io"

# Rangers FC ID in API-Football
RANGERS_ID = 257


def get_fixtures():

    api_key = os.environ.get("API_FOOTBALL_KEY")

    if not api_key:
        raise Exception("Missing API_FOOTBALL_KEY")


    headers = {
        "x-apisports-key": api_key
    }


    params = {
    "team": RANGERS_ID,
    "season": 2026,
    "league": 179
    }


    response = requests.get(
        f"{API_URL}/fixtures",
        headers=headers,
        params=params
    )


    response.raise_for_status()

    data = response.json()

    print(data)


    fixtures = []


    for item in data.get("response", []):

        fixture = item["fixture"]
        teams = item["teams"]
        league = item["league"]


        # Convert API date to XMLTV format
        kickoff = datetime.fromisoformat(
            fixture["date"].replace("Z", "+00:00")
        )


        xml_time = (
            kickoff.strftime("%Y%m%d%H%M%S")
            + " +0000"
        )


        stadium = "Unknown"

        if fixture.get("venue"):
            stadium = fixture["venue"].get(
                "name",
                "Unknown"
            )


        fixtures.append({

            "home": teams["home"]["name"],

            "away": teams["away"]["name"],

            "competition":
                league["name"],

            "stadium":
                stadium,

            "kickoff":
                xml_time,

            "tv":
                ""

        })


    return fixtures
