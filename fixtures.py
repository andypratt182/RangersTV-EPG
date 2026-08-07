import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone


BBC_FIXTURES_URL = (
    "https://www.bbc.co.uk/sport/football/teams/rangers/scores-fixtures"
)


def get_fixtures():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(compatible; RangersTV-EPG/1.0)"
        )
    }

    response = requests.get(
        BBC_FIXTURES_URL,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    fixtures = []


    # BBC embeds fixture data in JSON
    scripts = soup.find_all(
        "script"
    )


    for script in scripts:

        if not script.string:
            continue

        text = script.string

        if "Rangers" not in text:
            continue


        # Look for ISO dates
        import re

        dates = re.findall(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
            text
        )


        for date in dates:

            kickoff = datetime.fromisoformat(
                date
            ).replace(
                tzinfo=timezone.utc
            )


            if kickoff < datetime.now(timezone.utc):
                continue


            fixtures.append({

                "home": "Rangers",

                "away": extract_opponent(text),

                "competition":
                    "Football",

                "stadium":
                    "Ibrox Stadium",

                "kickoff":
                    kickoff.strftime(
                        "%Y%m%d%H%M%S +0000"
                    ),

                "tv":
                    ""

            })


    fixtures.sort(
        key=lambda x: x["kickoff"]
    )


    return fixtures
