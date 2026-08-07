import os
import requests
from datetime import datetime


API_KEY = os.environ.get("API_FOOTBALL_KEY")

BASE_URL = "https://v3.football.api-sports.io"

# Rangers FC ID on API-Football
RANGERS_ID = 257


def get_fixtures():

    headers = {
        "x-apisports-key": API_KEY
    }


    params = {
        "team": RANGERS_ID,
        "next": 20
    }


    response = requests.get(
        f"{BASE_URL}/fixtures",
        headers=headers,
        params=params
    )


    data = response.json()


    fixtures = []


    for game in data.get("response", []):

        fixture = game["fixture"]
        teams = game["teams"]
        league = game["league"]


        kickoff = datetime.fromisoformat(
            fixture["date"].replace("Z", "+00:00")
        )


        kickoff_xml = kickoff.strftime(
            "%Y%m%d%H%M%S"
        ) + " +0000"


        home = teams["home"]["name"]
        away = teams["away"]["name"]


        fixtures.append({

            "home": home,

            "away": away,

            "competition":
                league["name"],

            "stadium":
                fixture["venue"]["name"]
                if fixture["venue"]["name"]
                else "Unknown",

            "kickoff":
                kickoff_xml,

            "tv":
                ""

        })


    return fixtures
