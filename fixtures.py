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

# Scottish Premiership
SCOTTISH_PREMIERSHIP_ID = 501


# ============================================================
# SPORTMONKS API HELPER
# ============================================================

def sportmonks_get(endpoint, token, params=None):

    url = (
        f"{SPORTMONKS_BASE_URL}/{endpoint}"
    )

    request_params = {
        "api_token": token
    }

    if params:
        request_params.update(params)


    headers = {
        "Accept": "application/json"
    }


    response = requests.get(
        url,
        headers=headers,
        params=request_params,
        timeout=20
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
            "name"
        ) in (
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
        "Sportmonks does not currently "
        "provide the 2026/27 Scottish "
        "Premiership season."
    )


# ============================================================
# NORMALISE TEAM NAME
# ============================================================

def normalise_team_name(name):

    if not name:

        return ""


    name = name.lower().strip()


    # Only remove suffixes.
    #
    # Do NOT remove words such as "the".
    # For example:
    #
    # Motherwell -> motherwell
    #
    # not:
    #
    # morwell

    replacements = [
        " football club",
        " fc"
    ]


    for replacement in replacements:

        if name.endswith(
            replacement
        ):

            name = name[
                :-len(replacement)
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
            "channel_id": channel_id,

            "name": channel_name,

            "stadium": team.get(
                "stadium",
                "Venue TBC"
            )
        }


    return allowed


# ============================================================
# GET HOME / AWAY TEAMS
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


    # Fallback
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
# PARSE SPORTMONKS DATETIME
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
            "WARNING: Unable to parse "
            f"kickoff: {value}"
        )

        return None


    # Sportmonks can return a timestamp
    # without timezone information.
    #
    # Treat it as UTC.

    if kickoff.tzinfo is None:

        kickoff = kickoff.replace(
            tzinfo=timezone.utc
        )


    return kickoff


# ============================================================
# GET FIXTURES
# ============================================================

def get_fixtures(team):

    """
    Get upcoming Scottish Premiership fixtures
    using Sportmonks.

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


    now = datetime.now(
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
    # Get 2026/27 season
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
    # Retrieve season fixtures
    #
    # IMPORTANT:
    # We deliberately do NOT use:
    #
    # filters=seasonId:28275
    #
    # because Sportmonks rejected that filter.
    #
    # Instead we use the season endpoint.
    # --------------------------------------------------------

    print()
    print("==============================")
    print(
        "Downloading 2026/27 "
        "Scottish Premiership fixtures"
    )
    print("==============================")


    endpoint = (
        f"fixtures/seasons/{season_id}"
    )


    data = sportmonks_get(
        endpoint,
        token,
        {
            "include": (
                "participants;"
                "league"
            )
        }
    )


    events = data.get(
        "data",
        []
    )


    print(
        f"Sportmonks returned "
        f"{len(events)} fixture(s) "
        f"for season {season_id}"
    )


    if not events:

        print()
        print(
            "WARNING: No fixtures returned "
            "for the 2026/27 season."
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


        # Ignore matches outside our requested
        # 24-day window.

        if kickoff < datetime.combine(
            start_date,
            datetime.min.time(),
            tzinfo=UK_TZ
        ):

            continue


        if kickoff > datetime.combine(
            end_date,
            datetime.max.time(),
            tzinfo=UK_TZ
        ):

            continue


        # Ignore completed fixtures.

        if kickoff <= now:

            continue


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

        event_league = event.get(
            "league",
            {}
        )


        competition = event_league.get(
            "name",
            "Premiership"
        )


        # ----------------------------------------------------
        # YOUR stadium mapping
        # ----------------------------------------------------

        stadium = matched_team[
            "stadium"
        ]


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
        # Diagnostic output
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
            f"{kickoff.astimezone(UK_TZ)}"
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
    # Sort
    # --------------------------------------------------------

    fixtures.sort(
        key=lambda x:
        x["kickoff"]
    )


    print()
    print("==============================")
    print(
        f"Found {len(fixtures)} "
        f"upcoming fixtures for "
        f"{team['name']}"
    )
    print("==============================")


    if not fixtures:

        print(
            f"No upcoming fixtures for "
            f"{team['name']}"
        )


    return fixtures
