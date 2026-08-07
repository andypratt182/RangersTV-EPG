import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


BBC_FIXTURES_URL = (
    "https://web-cdn.api.bbci.co.uk/"
    "wc-poll-data/container/sport-data-scores-fixtures"
)

UK_TZ = ZoneInfo("Europe/London")


def get_fixtures(team_urn):
    """
    Get upcoming fixtures for a BBC Sports team.

    team_urn example:
    urn:bbc:sportsdata:football:team:rangers
    """

    # Use UK date rather than UTC date.
    today = datetime.now(UK_TZ).date()

    # The BBC endpoint has been tested with a 24-day window.
    start_date = today + timedelta(days=1)
    end_date = today + timedelta(days=24)

    params = {
        "selectedStartDate": start_date.isoformat(),
        "selectedEndDate": end_date.isoformat(),
        "todayDate": today.isoformat(),
        "urn": team_urn,
    }

    headers = {
        "User-Agent": "RangersTV-EPG/1.0",
        "Accept": "application/json",
    }

    response = requests.get(
        BBC_FIXTURES_URL,
        params=params,
        headers=headers,
        timeout=20,
    )

    if not response.ok:
        print("BBC request failed")
        print("Status:", response.status_code)
        print("URL:", response.url)
        print("Response:", response.text[:1000])

        response.raise_for_status()

    data = response.json()

    fixtures = []

    # Walk through the BBC JSON structure.
    for event_group in data.get("eventGroups", []):

        for secondary_group in event_group.get(
            "secondaryGroups",
            []
        ):

            competition = secondary_group.get(
                "displayLabel",
                "Football",
            )

            for event in secondary_group.get(
                "events",
                []
            ):

                # BBC supplies kickoff in UTC.
                kickoff = datetime.fromisoformat(
                    event["startDateTime"].replace(
                        "Z",
                        "+00:00",
                    )
                )

                # Ignore fixtures that have already started.
                if kickoff < datetime.now(timezone.utc):
                    continue

                home = event["home"]["fullName"]
                away = event["away"]["fullName"]

                # Determine the venue.
                if home == "Rangers":
                    stadium = "Ibrox Stadium"
                else:
                    stadium = "Away"

                fixtures.append(
                    {
                        "home": home,
                        "away": away,
                        "competition": competition,
                        "stadium": stadium,
                        "kickoff": kickoff.strftime(
                            "%Y%m%d%H%M%S +0000"
                        ),
                        "tv": "",
                    }
                )

    # Sort chronologically.
    fixtures.sort(
        key=lambda x: x["kickoff"]
    )

    return fixtures
