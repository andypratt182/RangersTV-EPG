import requests
from datetime import datetime, timezone


TEAM_ID = "133602"   # Rangers FC on TheSportsDB


def get_fixtures():

    url = (
        f"https://www.thesportsdb.com/api/v1/json/3/"
        f"eventsnext.php?id={TEAM_ID}"
    )

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    fixtures = []

    for event in data.get("events", []):

        if not event:
            continue

        date = event.get("dateEvent")
        time = event.get("strTime")

        if not date:
            continue

        if not time:
            time = "15:00:00"

        kickoff = datetime.strptime(
            f"{date} {time}",
            "%Y-%m-%d %H:%M:%S"
        )

        kickoff = kickoff.replace(
            tzinfo=timezone.utc
        )

        if kickoff < datetime.now(timezone.utc):
            continue


        fixtures.append({

            "home": event.get(
                "strHomeTeam",
                "Unknown"
            ),

            "away": event.get(
                "strAwayTeam",
                "Unknown"
            ),

            "competition": event.get(
                "strLeague",
                "Football"
            ),

            "stadium": event.get(
                "strVenue",
                "Ibrox Stadium"
            ),

            "kickoff":
                kickoff.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),

            "tv": ""

        })


    fixtures.sort(
        key=lambda x: x["kickoff"]
    )


    return fixtures
