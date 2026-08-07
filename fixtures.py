import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from teams import SPFL_TEAMS


BBC_FIXTURES_URL = (
    "https://web-cdn.api.bbci.co.uk/"
    "wc-poll-data/container/sport-data-scores-fixtures"
)

UK_TZ = ZoneInfo("Europe/London")


def get_home_stadium(home_team):

    for team in SPFL_TEAMS.values():

        team_name = team["name"].replace(
            " TV",
            ""
        )

        if team_name == home_team:
            return team["stadium"]

    return "Venue TBC"


def get_fixtures(team):
    """
    Get upcoming fixtures for one SPFL team
    from the BBC Sport JSON feed.
    """

    team_urn = team["urn"]

    today = datetime.now(UK_TZ).date()

    start_date = today + timedelta(days=1)
    end_date = today + timedelta(days=24)

    params = {
        "selectedStartDate": start_date.isoformat(),
        "selectedEndDate": end_date.isoformat(),
        "todayDate": today.isoformat(),
        "urn": team_urn,
    }

    headers = {
        "User-Agent": "SPFL-EPG/1.0",
        "Accept": "application/json",
    }

    response = requests.get(
        BBC_FIXTURES_URL,
        params=params,
        headers=headers,
        timeout=20,
    )

    if not response.ok:

        print(
            f"BBC request failed for {team['name']}"
        )

        print(
            "Status:",
            response.status_code
        )

        print(
            "URL:",
            response.url
        )

        print(
            "Response:",
            response.text[:1000]
        )

        response.raise_for_status()


    data = response.json()

    fixtures = []


    for event_group in data.get(
        "eventGroups",
        []
    ):

        for secondary_group in event_group.get(
            "secondaryGroups",
            []
        ):

            competition = secondary_group.get(
                "displayLabel",
                "Football"
            )


            for event in secondary_group.get(
                "events",
                []
            ):

                kickoff = datetime.fromisoformat(
                    event["startDateTime"].replace(
                        "Z",
                        "+00:00"
                    )
                )


                if kickoff < datetime.now(
                    timezone.utc
                ):
                    continue


                home_team = event["home"]["fullName"]


                fixtures.append(
                    {
                        "channel": team["name"],

                        "channel_id": None,

                        "home":
                            home_team,

                        "away":
                            event["away"]["fullName"],

                        "competition":
                            competition,

                        "stadium":
                            get_home_stadium(
                                home_team
                            ),

                        "kickoff":
                            kickoff.strftime(
                                "%Y%m%d%H%M%S +0000"
                            ),

                        "tv": "",
                    }
                )


    fixtures.sort(
        key=lambda x: x["kickoff"]
    )


    return fixtures
