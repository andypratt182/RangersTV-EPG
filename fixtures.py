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
            response.text[:2000]
        )

        print()

        response.raise_for_status()


    return response.json()


# ============================================================
# FIND SCOTTISH PREMIERSHIP
# ============================================================

def find_scottish_premiership(token):

    print()
    print("==============================")
    print("Searching for Scottish Premiership")
    print("==============================")


    data = sportmonks_get(
        "leagues/search/Premiership",
        token
    )


    leagues = data.get(
        "data",
        []
    )


    if not leagues:

        raise RuntimeError(
            "Sportmonks returned no leagues "
            "matching Premiership."
        )


    print(
        f"Found {len(leagues)} matching league(s)"
    )


    for league in leagues:

        print(
            f"  ID {league.get('id')}: "
            f"{league.get('name')}"
        )


    # Prefer an exact Scottish Premiership match
    for league in leagues:

        name = (
            league.get("name") or ""
        ).lower()


        country = (
            league.get("country") or {}
        ).get(
            "name",
            ""
        ).lower()


        if (
            "premiership" in name
            and "scotland" in country
        ):

            print()
            print(
                "Selected league:"
            )

            print(
                f"  ID: {league['id']}"
            )

            print(
                f"  Name: {league.get('name')}"
            )

            print(
                f"  Country: "
                f"{(league.get('country') or {}).get('name')}"
            )


            return league


    # Fallback if country isn't included
    for league in leagues:

        name = (
            league.get("name") or ""
        ).lower()


        if name == "premiership":

            print()
            print(
                "WARNING: Using Premiership "
                "league based on name only."
            )


            return league


    raise RuntimeError(
        "Could not identify Scottish Premiership."
    )


# ============================================================
# FIND 2026/27 SEASON
# ============================================================

def find_2026_27_season(
    token,
    league_id
):

    print()
    print("==============================")
    print("Finding 2026/27 season")
    print("==============================")


    data = sportmonks_get(
        f"leagues/{league_id}",
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

        season_id = season.get(
            "id"
        )

        season_name = season.get(
            "name",
            ""
        )


        print(
            f"  ID {season_id}: "
            f"{season_name}"
        )


    # Accept either common naming format
    target_names = {
        "2026/2027",
        "2026/27"
    }


    for season in seasons:

        if season.get(
            "name"
        ) in target_names:

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


    print()
    print(
        "WARNING: Sportmonks does not currently "
        "provide a 2026/27 Scottish Premiership "
        "season for this account."
    )

    print(
        "The latest available season is:"
    )


    if seasons:

        latest = max(
            seasons,
            key=lambda x: x.get("name", "")
        )


        print(
            f"  ID: {latest.get('id')}"
        )

        print(
            f"  Name: {latest.get('name')}"
        )


    print()
    print(
        "No season-specific filtering will be "
        "applied until 2026/27 becomes available."
    )


    return None


# ============================================================
# NORMALISE TEAM NAME
# ============================================================

def normalise_team_name(name):

    if not name:

        return ""


    name = name.lower().strip()


    # Remove common suffixes only.
    # DO NOT remove arbitrary words such as "the",
    # because they can occur inside legitimate names.
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
# PARSE SPORTMONKS DATETIME SAFELY
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


    # Sportmonks may return a datetime
    # without timezone information.
    #
    # Treat naive Sportmonks values as UTC.
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
    Get upcoming Scottish fixtures for one
    configured SPFL channel.

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
    # League
    # --------------------------------------------------------

    league = find_scottish_premiership(
        token
    )


    league_id = league[
        "id"
    ]


    # --------------------------------------------------------
    # Season
    # --------------------------------------------------------

    season = find_2026_27_season(
        token,
        league_id
    )


    # --------------------------------------------------------
    # Retrieve fixtures
    # --------------------------------------------------------

    print()
    print("==============================")
    print("Downloading fixtures")
    print("==============================")


    endpoint = (
        f"fixtures/between/"
        f"{start_date}/"
        f"{end_date}"
    )


    params = {
        "include": (
            "participants;"
            "league"
        )
    }


    # If the 2026/27 season exists,
    # restrict the request to it.
    if season:

        params[
            "filters"
        ] = f"seasonId:{season['id']}"


    data = sportmonks_get(
        endpoint,
        token,
        params
    )


    events = data.get(
        "data",
        []
    )


    print(
        f"Sportmonks returned "
        f"{len(events)} fixture(s)"
    )


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
    # Process events
    # --------------------------------------------------------

    for event in events:

        kickoff = parse_kickoff(
            event.get(
                "starting_at"
            )
        )


        if kickoff is None:

            continue


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
            "Scottish Premiership"
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
