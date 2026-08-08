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


# ------------------------------------------------------------
# API helper
# ------------------------------------------------------------

def sportmonks_get(endpoint, token, params=None):

    url = (
        f"{SPORTMONKS_BASE_URL}"
        f"/{endpoint}"
    )

    headers = {
        "Accept": "application/json",
    }

    request_params = {
        "api_token": token
    }

    if params:
        request_params.update(params)


    response = requests.get(
        url,
        headers=headers,
        params=request_params,
        timeout=20,
    )


    if not response.ok:

        print()
        print("Sportmonks API ERROR")
        print("--------------------")
        print("Status:", response.status_code)
        print("URL:", response.url)
        print(
            "Response:",
            response.text[:2000]
        )
        print()

        response.raise_for_status()


    return response.json()


# ------------------------------------------------------------
# Find Scottish Premiership
# ------------------------------------------------------------

def find_scottish_premiership(token):

    print()
    print("==============================")
    print("Searching Sportmonks leagues")
    print("==============================")


    data = sportmonks_get(
        "leagues/search/Premiership",
        token,
    )


    leagues = data.get(
        "data",
        []
    )


    if not leagues:

        raise RuntimeError(
            "Sportmonks returned no leagues "
            "matching 'Premiership'"
        )


    print(
        f"Found {len(leagues)} matching league(s)"
    )


    for league in leagues:

        print(
            f"  ID {league.get('id')}: "
            f"{league.get('name')} "
            f"({league.get('short_code', '')})"
        )


    # Look specifically for Scottish Premiership
    for league in leagues:

        name = (
            league.get("name") or ""
        ).lower()

        country = (
            league.get("country", {})
            .get("name", "")
        ).lower()


        if (
            "scotland" in country
            and "premiership" in name
        ):

            print()
            print(
                "Selected Scottish Premiership:"
            )
            print(
                f"  ID: {league['id']}"
            )
            print(
                f"  Name: {league.get('name')}"
            )
            print(
                f"  Country: "
                f"{league.get('country', {}).get('name')}"
            )

            return league


    # Fallback based purely on name
    for league in leagues:

        name = (
            league.get("name") or ""
        ).lower()

        if name == "premiership":

            print()
            print(
                "WARNING: Could not verify "
                "Scottish country."
            )

            print(
                "Using league:",
                league.get("name"),
                league.get("id"),
            )

            return league


    raise RuntimeError(
        "Could not identify the Scottish "
        "Premiership in Sportmonks."
    )


# ------------------------------------------------------------
# Find current 2026/27 season
# ------------------------------------------------------------

def find_current_season(
    token,
    league_id,
):

    print()
    print("==============================")
    print("Finding Scottish Premiership season")
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


    if not seasons:

        raise RuntimeError(
            "Sportmonks returned no seasons "
            "for the Scottish Premiership."
        )


    print(
        f"Found {len(seasons)} season(s)"
    )


    # We want 2026/27.
    # Sportmonks normally represents this
    # using year 2026.

    target_season = None


    for season in seasons:

        season_name = (
            season.get("name") or ""
        )

        season_year = season.get(
            "year"
        )


        print(
            f"  ID {season.get('id')}: "
            f"{season_name} "
            f"(year={season_year}, "
            f"active={season.get('is_current', season.get('active'))})"
        )


        if (
            season_year == 2026
            or "2026/27" in season_name
            or "2026" in season_name
        ):

            target_season = season
            break


    if target_season is None:

        raise RuntimeError(
            "Could not find the 2026/27 "
            "Scottish Premiership season "
            "in Sportmonks."
        )


    print()
    print(
        "Selected season:"
    )

    print(
        f"  ID: {target_season['id']}"
    )

    print(
        f"  Name: {target_season.get('name')}"
    )

    print(
        f"  Year: {target_season.get('year')}"
    )


    return target_season


# ------------------------------------------------------------
# Normalise team names
# ------------------------------------------------------------

def normalise_team_name(name):

    if not name:
        return ""


    name = name.lower().strip()


    replacements = {
        "fc": "",
        "football club": "",
        "the": "",
        "  ": " ",
    }


    for old, new in replacements.items():

        name = name.replace(
            old,
            new
        )


    return " ".join(
        name.split()
    ).strip()


# ------------------------------------------------------------
# Build allowed SPFL team names
# ------------------------------------------------------------

def get_allowed_team_names():

    allowed = {}


    for channel_id, team in SPFL_TEAMS.items():

        channel_name = team["name"]


        # Remove " TV" because that is the
        # IPTV channel name, not the football club.
        football_name = channel_name

        if football_name.endswith(" TV"):

            football_name = football_name[:-3]


        allowed[
            normalise_team_name(
                football_name
            )
        ] = {
            "channel_id": channel_id,
            "name": channel_name,
            "stadium": team.get(
                "stadium",
                "Venue TBC"
            ),
        }


    return allowed


# ------------------------------------------------------------
# Extract participant names
# ------------------------------------------------------------

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


    # Diagnostic fallback
    if not home or not away:

        names = [
            p.get("name", "")
            for p in participants
        ]


        if len(names) >= 2:

            if not home:
                home = names[0]

            if not away:
                away = names[1]


    return home, away


# ------------------------------------------------------------
# Main fixture function
# ------------------------------------------------------------

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
        f"  Start: {start_date}"
    )

    print(
        f"  End:   {end_date}"
    )


    # --------------------------------------------------------
    # Find league
    # --------------------------------------------------------

    league = find_scottish_premiership(
        token
    )


    league_id = league["id"]


    # --------------------------------------------------------
    # Find season
    # --------------------------------------------------------

    season = find_current_season(
        token,
        league_id
    )


    season_id = season["id"]


    # --------------------------------------------------------
    # Retrieve fixtures by date range
    #
    # Sportmonks documents this endpoint as:
    #
    # /fixtures/between/{start}/{end}
    #
    # --------------------------------------------------------

    print()
    print(
        "=============================="
    )

    print(
        "Downloading Scottish Premiership fixtures"
    )

    print(
        "=============================="
    )


    endpoint = (
        f"fixtures/between/"
        f"{start_date}/"
        f"{end_date}"
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
        f"{len(events)} fixture(s)"
    )


    if not events:

        print()
        print(
            "WARNING: Sportmonks returned "
            "zero fixtures."
        )

        print(
            "This may mean the Scottish "
            "Premiership is not available "
            "to this API subscription, "
            "or the season/date range "
            "contains no fixtures."
        )

        return []


    # --------------------------------------------------------
    # Build allowed team list
    # --------------------------------------------------------

    allowed_teams = (
        get_allowed_team_names()
    )


    print()
    print(
        "Configured SPFL teams:"
    )


    for key, value in allowed_teams.items():

        print(
            f"  {value['name']} "
            f"-> Sportmonks match name key: "
            f"'{key}'"
        )


    fixtures = []


    # --------------------------------------------------------
    # Process events
    # --------------------------------------------------------

    for event in events:

        starting_at = event.get(
            "starting_at"
        )


        if not starting_at:

            print(
                "WARNING: Fixture has no "
                "starting_at value. Skipping."
            )

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
                "WARNING: Could not parse "
                f"kickoff: {starting_at}"
            )

            continue


        if kickoff <= datetime.now(
            timezone.utc
        ):

            continue


        home, away = get_participants(
            event
        )


        if not home or not away:

            print(
                "WARNING: Could not identify "
                "home/away teams."
            )

            print(
                "Event:",
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
        # Check whether either team is one of
        # our configured 12 SPFL channels.
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


        if matched_team is None:

            # This is normal because the date-range
            # endpoint returns all accessible fixtures.
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
        # Use YOUR stadium mapping
        # ----------------------------------------------------

        stadium = matched_team[
            "stadium"
        ]


        fixture = {
            "channel": matched_team[
                "name"
            ],

            "channel_id": None,

            "home": home,

            "away": away,

            "competition": competition,

            "stadium": stadium,

            "kickoff": kickoff.strftime(
                "%Y%m%d%H%M%S +0000"
            ),

            "tv": "",
        }


        fixtures.append(
            fixture
        )


        print()
        print(
            "MATCHED:"
        )

        print(
            f"  Channel: "
            f"{matched_team['name']}"
        )

        print(
            f"  Match: "
            f"{home} vs {away}"
        )

        print(
            f"  Competition: "
            f"{competition}"
        )

        print(
            f"  Stadium: "
            f"{stadium}"
        )

        print(
            f"  Kick-off: "
            f"{kickoff.astimezone(UK_TZ)}"
        )


    # --------------------------------------------------------
    # Remove duplicate fixtures
    # --------------------------------------------------------

    unique = {}


    for fixture in fixtures:

        key = (
            fixture["kickoff"],
            fixture["home"],
            fixture["away"],
            fixture["channel"],
        )


        unique[key] = fixture


    fixtures = list(
        unique.values()
    )


    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    fixtures.sort(
        key=lambda x: x["kickoff"]
    )


    print()
    print(
        "=============================="
    )

    print(
        f"Found {len(fixtures)} "
        f"upcoming SPFL fixtures "
        f"for {team['name']}"
    )

    print(
        "=============================="
    )


    return fixtures
