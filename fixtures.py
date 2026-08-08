import os
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from teams import SPFL_TEAMS


SPORTMONKS_BASE_URL = (
    "https://api.sportmonks.com/v3/football"
)

UK_TZ = ZoneInfo("Europe/London")

FIXTURE_DAYS = 24

# Confirmed Sportmonks IDs
SCOTTISH_PREMIERSHIP_ID = 501
SCOTTISH_PREMIERSHIP_2026_27_ID = 28275


# ============================================================
# SPORTMONKS API
# ============================================================

def sportmonks_get(
    endpoint,
    token,
    params=None
):

    url = (
        f"{SPORTMONKS_BASE_URL}/{endpoint}"
    )


    request_params = {
        "api_token": token
    }


    if params:

        request_params.update(
            params
        )


    response = requests.get(
        url,
        params=request_params,
        headers={
            "Accept": "application/json"
        },
        timeout=30
    )


    if not response.ok:

        print()
        print("==============================")
        print("SPORTMONKS API ERROR")
        print("==============================")

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
            response.text[:3000]
        )

        print()

        response.raise_for_status()


    return response.json()


# ============================================================
# VERIFY 2026/27 SEASON
# ============================================================

def verify_2026_27_season(token):

    print()
    print("==============================")
    print("Checking Scottish Premiership season")
    print("==============================")


    print(
        f"League ID: "
        f"{SCOTTISH_PREMIERSHIP_ID}"
    )


    data = sportmonks_get(
        f"leagues/{SCOTTISH_PREMIERSHIP_ID}",
        token,
        {
            "include": "seasons"
        }
    )


    league = data.get(
        "data",
        {}
    )


    seasons = league.get(
        "seasons",
        []
    )


    print(
        f"Found {len(seasons)} season(s)"
    )


    for season in seasons:

        print(
            f"  ID {season.get('id')}: "
            f"{season.get('name')}"
        )


    for season in seasons:

        if season.get(
            "id"
        ) == SCOTTISH_PREMIERSHIP_2026_27_ID:

            print()
            print(
                "Confirmed 2026/27 season:"
            )

            print(
                f"  ID: {season.get('id')}"
            )

            print(
                f"  Name: {season.get('name')}"
            )


            return season


    # The season was already confirmed during
    # our previous test. If the relationship is
    # unavailable now, give a useful diagnostic.

    print()
    print(
        "WARNING: Season 28275 was not returned "
        "by the seasons relationship."
    )

    print(
        "The season ID was previously confirmed "
        "as 2026/2027."
    )


    return {
        "id":
            SCOTTISH_PREMIERSHIP_2026_27_ID,

        "name":
            "2026/2027"
    }


# ============================================================
# NORMALISE TEAM NAME
# ============================================================

def normalise_team_name(name):

    if not name:

        return ""


    name = name.lower().strip()


    for suffix in (
        " football club",
        " fc"
    ):

        if name.endswith(
            suffix
        ):

            name = name[
                :-len(suffix)
            ].strip()


    return " ".join(
        name.split()
    )


# ============================================================
# BUILD TEAM MATCHING
# ============================================================

def get_allowed_team_names():

    allowed = {}


    for channel_id, team in SPFL_TEAMS.items():

        channel_name = team[
            "name"
        ]


        football_name = channel_name


        if football_name.endswith(
            " TV"
        ):

            football_name = football_name[
                :-3
            ]


        normalised = normalise_team_name(
            football_name
        )


        allowed[
            normalised
        ] = {

            "channel_id":
                channel_id,

            "name":
                channel_name,

            "stadium":
                team.get(
                    "stadium",
                    "Venue TBC"
                )
        }


    return allowed


# ============================================================
# PARSE KICKOFF
# ============================================================

def parse_kickoff(value):

    if not value:

        return None


    try:

        kickoff = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )


    except ValueError:

        print(
            "WARNING: Could not parse "
            f"kickoff: {value}"
        )

        return None


    if kickoff.tzinfo is None:

        kickoff = kickoff.replace(
            tzinfo=timezone.utc
        )


    return kickoff


# ============================================================
# GET PARTICIPANTS
# ============================================================

def get_participants(event):

    participants = event.get(
        "participants",
        []
    )


    home = None
    away = None


    for participant in participants:

        name = participant.get(
            "name",
            ""
        )


        meta = participant.get(
            "meta",
            {}
        )


        location = meta.get(
            "location"
        )


        if location == "home":

            home = name


        elif location == "away":

            away = name


    # Fallback if location metadata isn't available.

    if not home or not away:

        names = [
            p.get(
                "name",
                ""
            )
            for p in participants
        ]


        if len(names) >= 2:

            if not home:

                home = names[0]


            if not away:

                away = names[1]


    return home, away


# ============================================================
# EXTRACT FIXTURES FROM SCHEDULE
# ============================================================

def extract_schedule_fixtures(data):

    fixtures = []


    def walk(value):

        if isinstance(
            value,
            dict
        ):

            # Fixture objects contain all three
            # of these fields.

            if (
                value.get("id") is not None
                and value.get("starting_at") is not None
                and "participants" in value
            ):

                fixtures.append(
                    value
                )


            for child in value.values():

                walk(child)


        elif isinstance(
            value,
            list
        ):

            for child in value:

                walk(child)


    walk(data)


    # Remove duplicate fixture IDs.

    unique = {}


    for fixture in fixtures:

        fixture_id = fixture.get(
            "id"
        )


        if fixture_id is not None:

            unique[
                fixture_id
            ] = fixture


    return list(
        unique.values()
    )


# ============================================================
# GET FIXTURES
# ============================================================

def get_fixtures(team):

    """
    Get upcoming Scottish Premiership fixtures.

    Existing output structure is preserved.
    """


    token = os.getenv(
        "SPORTMONKS_API_TOKEN"
    )


    if not token:

        raise RuntimeError(
            "SPORTMONKS_API_TOKEN environment "
            "variable is not set."
        )


    now_utc = datetime.now(
        timezone.utc
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


    print()
    print(
        "Sportmonks fixture window:"
    )

    print(
        f"  {start_date} → {end_date}"
    )


    # --------------------------------------------------------
    # Confirm season
    # --------------------------------------------------------

    season = verify_2026_27_season(
        token
    )


    season_id = season[
        "id"
    ]


    print()
    print(
        f"Using season ID: {season_id}"
    )


    # --------------------------------------------------------
    # Download season schedule
    # --------------------------------------------------------

    print()
    print("==============================")
    print(
        "Downloading 2026/27 "
        "Scottish Premiership schedule"
    )
    print("==============================")


    endpoint = (
        f"schedules/seasons/{season_id}"
    )


    data = sportmonks_get(
        endpoint,
        token
    )


    # --------------------------------------------------------
    # Extract fixtures
    # --------------------------------------------------------

    events = extract_schedule_fixtures(
        data
    )


    print()
    print(
        f"Schedule contains "
        f"{len(events)} fixture(s)"
    )


    if not events:

        print()
        print(
            "WARNING: No fixtures were found "
            "in the Sportmonks schedule."
        )

        return []


    # --------------------------------------------------------
    # Configured teams
    # --------------------------------------------------------

    allowed_teams = (
        get_allowed_team_names()
    )


    print()
    print(
        "Configured SPFL team matching:"
    )


    for key, value in allowed_teams.items():

        print(
            f"  {value['name']} "
            f"-> '{key}'"
        )


    fixtures = []


    # --------------------------------------------------------
    # Process fixtures
    # --------------------------------------------------------

    for event in events:

        kickoff = parse_kickoff(
            event.get(
                "starting_at"
            )
        )


        if kickoff is None:

            continue


        kickoff_uk = kickoff.astimezone(
            UK_TZ
        )


        # Date window

        if kickoff_uk.date() < start_date:

            continue


        if kickoff_uk.date() > end_date:

            continue


        # Already played

        if kickoff <= now_utc:

            continue


        # Teams

        home, away = get_participants(
            event
        )


        if not home or not away:

            print()
            print(
                "WARNING: Could not identify "
                "home/away teams."
            )

            print(
                "Fixture ID:",
                event.get("id")
            )

            continue


        home_key = normalise_team_name(
            home
        )

        away_key = normalise_team_name(
            away
        )


        matched_team = None


        if home_key in allowed_teams:

            matched_team = allowed_teams[
                home_key
            ]


        elif away_key in allowed_teams:

            matched_team = allowed_teams[
                away_key
            ]


        if matched_team is None:

            continue


        # ----------------------------------------------------
        # Competition
        # ----------------------------------------------------

        competition = "Premiership"


        league = event.get(
            "league"
        )


        if isinstance(
            league,
            dict
        ):

            competition = league.get(
                "name",
                competition
            )


        # ----------------------------------------------------
        # Stadium from teams.py
        # ----------------------------------------------------

        stadium = matched_team[
            "stadium"
        ]


        # ----------------------------------------------------
        # Preserve existing output structure
        # ----------------------------------------------------

        fixture = {

            "channel":
                matched_team["name"],

            "channel_id":
                None,

            "home":
                home,

            "away":
                away,

            "competition":
                competition,

            "stadium":
                stadium,

            "kickoff":
                kickoff.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),

            "tv":
                ""
        }


        fixtures.append(
            fixture
        )


        # ----------------------------------------------------
        # Diagnostic
        # ----------------------------------------------------

        print()
        print(
            "MATCHED FIXTURE"
        )

        print(
            "---------------"
        )

        print(
            f"Channel: "
            f"{matched_team['name']}"
        )

        print(
            f"Match: "
            f"{home} vs {away}"
        )

        print(
            f"Competition: "
            f"{competition}"
        )

        print(
            f"Stadium: "
            f"{stadium}"
        )

        print(
            f"Kick-off UK: "
            f"{kickoff_uk.strftime('%Y-%m-%d %H:%M')}"
        )

        print(
            f"Fixture ID: "
            f"{event.get('id')}"
        )


    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    unique = {}


    for fixture in fixtures:

        key = (
            fixture["channel"],
            fixture["kickoff"],
            fixture["home"],
            fixture["away"]
        )


        unique[key] = fixture


    fixtures = list(
        unique.values()
    )


    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    fixtures.sort(
        key=lambda x:
        x["kickoff"]
    )


    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    print()
    print("==============================")

    print(
        f"Found {len(fixtures)} "
        f"upcoming fixtures for "
        f"{team['name']}"
    )

    print(
        "==============================")


    if not fixtures:

        print(
            f"No upcoming fixtures for "
            f"{team['name']}"
        )


    return fixtures
