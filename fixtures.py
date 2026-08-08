import os
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


SPORTMONKS_URL = (
    "https://api.sportmonks.com/v3/football"
)

UK_TZ = ZoneInfo("Europe/London")

# How far ahead to retrieve fixtures
FIXTURE_DAYS = 24


def get_fixtures(team):
    """
    Get upcoming Scottish Premiership fixtures for one SPFL team
    using the Sportmonks API.

    The returned fixture structure is kept compatible with the
    existing generator.py and xmltv.py files.
    """

    api_token = os.getenv(
        "SPORTMONKS_API_TOKEN"
    )

    if not api_token:

        raise RuntimeError(
            "SPORTMONKS_API_TOKEN environment variable is not set"
        )


    today = datetime.now(
        UK_TZ
    ).date()

    start_date = today + timedelta(
        days=1
    )

    end_date = today + timedelta(
        days=FIXTURE_DAYS
    )


    # ---------------------------------------------------------
    # Find the Sportmonks team ID
    # ---------------------------------------------------------

    team_name = team["name"]

    search_url = (
        f"{SPORTMONKS_URL}/teams/search/"
        f"{team_name}"
    )


    headers = {
        "Accept": "application/json",
    }


    params = {
        "api_token": api_token,
    }


    response = requests.get(
        search_url,
        headers=headers,
        params=params,
        timeout=20,
    )


    if not response.ok:

        print(
            f"Sportmonks team lookup failed "
            f"for {team_name}"
        )

        print(
            "Status:",
            response.status_code
        )

        print(
            "Response:",
            response.text[:1000]
        )

        response.raise_for_status()


    team_data = response.json().get(
        "data",
        []
    )


    if not team_data:

        raise RuntimeError(
            f"Sportmonks could not find team: "
            f"{team_name}"
        )


    # Try to find an exact name match first
    sportmonks_team = None

    for candidate in team_data:

        candidate_name = candidate.get(
            "name",
            ""
        )

        if candidate_name.lower() == team_name.replace(
            " TV",
            ""
        ).lower():

            sportmonks_team = candidate
            break


    # If exact matching fails, use the first result
    if sportmonks_team is None:

        sportmonks_team = team_data[0]


    team_id = sportmonks_team["id"]


    print(
        f"Sportmonks team: "
        f"{sportmonks_team.get('name')} "
        f"(ID {team_id})"
    )


    # ---------------------------------------------------------
    # Request fixtures for this team and date range
    # ---------------------------------------------------------

    fixtures_url = (
        f"{SPORTMONKS_URL}/fixtures/"
        f"between/{start_date}/"
        f"{end_date}/{team_id}"
    )


    params = {
        "api_token": api_token,

        # Only request information we actually need
        "include": (
            "participants;"
            "league"
        ),
    }


    print(
        f"Requesting Sportmonks fixtures: "
        f"{start_date} → {end_date}"
    )


    response = requests.get(
        fixtures_url,
        headers=headers,
        params=params,
        timeout=20,
    )


    if not response.ok:

        print(
            f"Sportmonks fixture request failed "
            f"for {team_name}"
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
            response.text[:2000]
        )

        response.raise_for_status()


    data = response.json().get(
        "data",
        []
    )


    fixtures = []


    # ---------------------------------------------------------
    # Process fixtures
    # ---------------------------------------------------------

    for event in data:

        # Ignore anything that isn't a scheduled fixture
        starting_at = event.get(
            "starting_at"
        )

        if not starting_at:
            continue


        try:

            kickoff = datetime.fromisoformat(
                starting_at.replace(
                    "Z",
                    "+00:00"
                )
            )

        except ValueError:

            print(
                f"Unable to parse kickoff for "
                f"{team_name}: {starting_at}"
            )

            continue


        # Only future fixtures
        if kickoff <= datetime.now(
            timezone.utc
        ):
            continue


        # -----------------------------------------------------
        # Identify home and away teams
        # -----------------------------------------------------

        participants = event.get(
            "participants",
            []
        )


        home_team = None
        away_team = None


        for participant in participants:

            meta = participant.get(
                "meta",
                {}
            )

            location = meta.get(
                "location"
            )


            if location == "home":

                home_team = participant.get(
                    "name",
                    ""
                )


            elif location == "away":

                away_team = participant.get(
                    "name",
                    ""
                )


        # Fallback if the meta information isn't available
        if not home_team or not away_team:

            names = [
                p.get("name", "")
                for p in participants
            ]

            if len(names) >= 2:

                home_team = names[0]
                away_team = names[1]


        if not home_team or not away_team:

            print(
                f"Unable to identify teams for "
                f"fixture involving {team_name}"
            )

            continue


        # -----------------------------------------------------
        # Competition
        # -----------------------------------------------------

        league = event.get(
            "league",
            {}
        )

        competition = league.get(
            "name",
            "Scottish Premiership"
        )


        # -----------------------------------------------------
        # Keep your own stadium mapping
        #
        # This deliberately uses teams.py rather than the API.
        # -----------------------------------------------------

        stadium = team.get(
            "stadium",
            "Venue TBC"
        )


        # -----------------------------------------------------
        # Build the same structure used by your existing
        # generator.py
        # -----------------------------------------------------

        fixtures.append(
            {
                "channel": team["name"],

                "channel_id": None,

                "home": home_team,

                "away": away_team,

                "competition": competition,

                "stadium": stadium,

                "kickoff": kickoff.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),

                "tv": "",
            }
        )


    # ---------------------------------------------------------
    # Sort chronologically
    # ---------------------------------------------------------

    fixtures.sort(
        key=lambda x: x["kickoff"]
    )


    print(
        f"Found {len(fixtures)} upcoming "
        f"fixtures for {team['name']}"
    )


    return fixtures
