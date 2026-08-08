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

# Sportmonks league ID for Scottish Premiership
SCOTTISH_PREMIERSHIP_ID = 501


# ============================================================
# SPORTMONKS API HELPER
# ============================================================

def sportmonks_get(endpoint, token):

    url = (
        f"{SPORTMONKS_BASE_URL}/{endpoint}"
    )

    params = {
        "api_token": token
    }

    headers = {
        "Accept": "application/json"
    }


    response = requests.get(
        url,
        headers=headers,
        params=params,
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
# FIND 2026/27 SEASON
# ============================================================

def find_2026_27_season(token):

    print()
    print("==============================")
    print("Finding Scottish Premiership season")
    print("==============================")


    endpoint = (
        f"leagues/{SCOTTISH_PREMIERSHIP_ID}"
    )


    data = sportmonks_get(
        endpoint,
        token
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

        season_name = (
            season.get("name") or ""
        )


        if season_name in (
            "2026/2027",
            "2026/27"
        ):

            print()
            print(
                "Selected 2026/27 season:"
            )

            print(
                f"  ID: {season['id']}"
            )

            print(
                f"  Name: {season.get('name')}"
            )


            return season


    raise RuntimeError(
        "Sportmonks could not find "
        "the 2026/27 Scottish Premiership "
        "season."
    )


# ============================================================
# NORMALISE TEAM NAME
# ============================================================

def normalise_team_name(name):

    if not name:

        return ""


    name = name.lower().strip()


    # Only remove common suffixes.
    #
    # Do NOT remove words such as "the".
    # This prevents:
    #
    # Motherwell -> morwell
    #

    suffixes = [
        " football club",
        " fc"
    ]


    for suffix in suffixes:

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
# BUILD CONFIGURED TEAM LIST
# ============================================================

def get_allowed_team_names():

    allowed = {}


    for channel_id, team in SPFL_TEAMS.items():

        channel_name = team[
            "name"
        ]


        football_name = channel_name


        # Remove " TV" from the EPG channel name
        # when matching against Sportmonks.

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
# PARSE KICKOFF DATETIME
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


    # Sportmonks can occasionally return
    # a datetime without timezone information.
    #
    # Treat a naive timestamp as UTC.

    if kickoff.tzinfo is None:

        kickoff = kickoff.replace(
            tzinfo=timezone.utc
        )


    return kickoff


# ============================================================
# EXTRACT FIXTURE PARTICIPANTS
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


    # --------------------------------------------------------
    # Fallback
    #
    # If Sportmonks doesn't provide participant meta,
    # use the participant order.
    # --------------------------------------------------------

    if not home or not away:

        names = [
            participant.get(
                "name",
                ""
            )
            for participant in participants
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

def extract_schedule_fixtures(
    data
):

    """
    Sportmonks season schedules can contain
    stages, rounds and fixtures.

    This function walks through the schedule
    recursively so that small structural
    changes in the API response don't break
    the EPG.
    """

    fixtures = []


    def walk(
        value
    ):

        if isinstance(
            value,
            dict
        ):

            # A fixture normally has an ID,
            # starting_at and participants.

            if (
                "id" in value
                and "starting_at" in value
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
    Get upcoming Scottish Premiership fixtures
    using the Sportmonks season schedule endpoint.

    Output structure remains compatible with
    generator.py and xmltv.py.
    """


    token = os.getenv(
        "SPORTMONKS_API_TOKEN"
    )


    if not token:

        raise RuntimeError(
            "SPORTMONKS_API_TOKEN environment "
            "variable is not set."
        )


    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

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
    # Find season
    # --------------------------------------------------------

    season = find_2026_27_season(
        token
    )


    season_id = season[
        "id"
    ]


    print()
    print(
        "Using season ID:",
        season_id
    )


    # --------------------------------------------------------
    # Download complete season schedule
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
    # Extract fixture objects
    # --------------------------------------------------------

    events = extract_schedule_fixtures(
        data
    )


    print()
    print(
        f"Sportmonks schedule contains "
        f"{len(events)} fixture(s)"
    )


    if not events:

        print()
        print(
            "WARNING: No fixtures were found "
            "inside the season schedule."
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
    # Process schedule fixtures
    # --------------------------------------------------------

    for event in events:

        kickoff = parse_kickoff(
            event.get(
                "starting_at"
            )
        )


        if kickoff is None:

            continue


        # ----------------------------------------------------
        # Only include requested date window
        # ----------------------------------------------------

        kickoff_uk = kickoff.astimezone(
            UK_TZ
        )


        if kickoff_uk.date() < start_date:

            continue


        if kickoff_uk.date() > end_date:

            continue


        # ----------------------------------------------------
        # Ignore matches already played
        # ----------------------------------------------------

        if kickoff <= now_utc:

            continue


        # ----------------------------------------------------
        # Get teams
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # Determine which EPG channel this fixture
        # belongs to.
        # ----------------------------------------------------

        matched_team = None


        if home_key in allowed_teams:

            matched_team = allowed_teams[
                home_key
            ]


        elif away_key in allowed_teams:

            matched_team = allowed_teams[
                away_key
            ]


        # Not one of our configured clubs.

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
        # Stadium
        #
        # Continue using your existing teams.py
        # stadium mapping.
        # ----------------------------------------------------

        stadium = matched_team[
            "stadium"
        ]


        # ----------------------------------------------------
        # Build output
        #
        # DO NOT change this structure.
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
        # Diagnostics
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
    # Final diagnostics
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
