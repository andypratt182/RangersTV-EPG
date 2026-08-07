import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone


RANGERS_FIXTURES_URL = (
    "https://www.rangers.co.uk/fixtures"
)


def get_fixtures():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(compatible; RangersTV-EPG/1.0)"
        )
    }


    response = requests.get(
        RANGERS_FIXTURES_URL,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    fixtures = []


    # Look for JSON-LD structured data
    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):

        try:
            data = script.string

            if not data:
                continue

            if "Rangers" not in data:
                continue


        except Exception:
            continue


    # Fallback parser for fixture cards
    fixture_blocks = soup.select(
        "[class*='fixture']"
    )


    for block in fixture_blocks:

        text = block.get_text(
            " ",
            strip=True
        )


        if "Rangers" not in text:
            continue


        # Basic extraction
        fixtures.append({

            "home": "Rangers",

            "away": text,

            "competition":
                "Rangers Fixture",

            "stadium":
                "Ibrox Stadium",

            "kickoff":
                "",

            "tv":
                ""

        })


    return fixtures
