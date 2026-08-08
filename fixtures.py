import os
import requests

from datetime import (
    datetime,
    timedelta,
    timezone
)

from zoneinfo import ZoneInfo

from teams import SPFL_TEAMS


SPORTMONKS_BASE_URL = (
    "https://api.sportmonks.com/v3/football"
)

UK_TZ = ZoneInfo(
    "Europe/London"
)

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

    # The season ID was previously confirmed
    # and works with this Sportmonks account.

    print()
    print(
        "WARNING: Season 28275 was not returned "
        "by the seasons relationship."
    )

    print(
        "Using previously confirmed season ID "
        "28275."
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

    # Sportmonks can occasionally return
    # a timezone-naive datetime.

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

    # Fallback if location metadata
    # isn't available.

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
# DOWNLOAD SCOTTISH PREMIERSHIP SCHEDULE ONCE
# ============================================================

def download_premiership_schedule():

    token = os.getenv(
        "SPORTMONKS_API_TOKEN"
    )

    if not token:

        raise RuntimeError(
            "SPORTMONKS_API_TOKEN environment "
            "variable is not set."
        )

    print()
    print("==========================================")
    print("SPORTMONKS SCOTTISH PREMIERSHIP DOWNLOAD")
    print("==========================================")

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

    print()
    print(
        "Downloading 2026/27 "
        "Scottish Premiership schedule..."
    )

    endpoint = (
        f"schedules/seasons/{season_id}"
    )

    data = sportmonks_get(
        endpoint,
        token
    )

    events = extract_schedule_fixtures(
        data
    )

    print()
    print(
        f"Sportmonks returned "
        f"{len(events)} fixture(s)"
    )

    return events


# ============================================================
# PROCESS COMPLETE SCHEDULE
# ============================================================

def build_fixtures(events):

    now_utc = datetime.now(
        timezone.utc
    )

    today = datetime.now(
        UK_TZ
    ).date()

    start_date = (
        today +
        timedelta(days=1)
    )

    end_date = (
        today +
        timedelta(days=FIXTURE_DAYS)
    )

    print()
    print("==============================")
    print("Sportmonks fixture window")
    print("==============================")

    print(
        f"{start_date} → {end_date}"
    )

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
            f"-> '{key}'"
        )

    # --------------------------------------------------------
    # Create an empty fixture list for every channel.
    # --------------------------------------------------------

    channel_fixtures = {}

    for team in SPFL_TEAMS.values():

        channel_name = team[
            "name"
        ]

        channel_fixtures[
            channel_name
        ] = []

    # --------------------------------------------------------
    # Process every Sportmonks fixture once.
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
        # Find ALL configured clubs involved.
        #
        # This deliberately uses two independent checks,
        # NOT if/elif.
        #
        # Therefore:
        #
        # Rangers vs Celtic
        #
        # is assigned to:
        #
        # Rangers TV
        # Celtic TV
        # ----------------------------------------------------

        matched_teams = []

        if home_key in allowed_teams:

            matched_teams.append(
                allowed_teams[
                    home_key
                ]
            )

        if away_key in allowed_teams:

            matched_teams.append(
                allowed_teams[
                    away_key
                ]
            )

        if not matched_teams:

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
        # Add the fixture to every relevant channel.
        # ----------------------------------------------------

        for matched_team in matched_teams:

            # Keep stadium based on the channel's
            # configured club.

            stadium = matched_team[
                "stadium"
            ]

            # ------------------------------------------------
            # Preserve existing output structure.
            # ------------------------------------------------

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

            channel_name = (
                matched_team["name"]
            )

            channel_fixtures[
                channel_name
            ].append(
                fixture
            )

            # ------------------------------------------------
            # Diagnostic output
            # ------------------------------------------------

            print()
            print(
                "MATCHED FIXTURE"
            )

            print(
                "---------------"
            )

            print(
                f"Channel: "
                f"{channel_name}"
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
    # Sort each channel chronologically.
    # --------------------------------------------------------

    for channel_name in channel_fixtures:

        channel_fixtures[
            channel_name
        ].sort(
            key=lambda x:
            x["kickoff"]
        )

    return channel_fixtures


# ============================================================
# CACHE
#
# The Sportmonks schedule is downloaded and processed
# only once during each generator.py run.
# ============================================================

_SCHEDULE_CACHE = None

_FIXTURE_CACHE = None


# ============================================================
# GET FIXTURES
# ============================================================

def get_fixtures(team):

    global _SCHEDULE_CACHE
    global _FIXTURE_CACHE

    # --------------------------------------------------------
    # Download and process the schedule only once.
    # --------------------------------------------------------

    if _FIXTURE_CACHE is None:

        _SCHEDULE_CACHE = (
            download_premiership_schedule()
        )

        _FIXTURE_CACHE = build_fixtures(
            _SCHEDULE_CACHE
        )

    channel_name = team[
        "name"
    ]

    fixtures = _FIXTURE_CACHE.get(
        channel_name,
        []
    )

    print()
    print("==============================")

    print(
        f"Found {len(fixtures)} "
        f"upcoming fixtures for "
        f"{channel_name}"
    )

    print(
        "=============================="
    )

    if not fixtures:

        print(
            f"No upcoming fixtures for "
            f"{channel_name}"
        )

    return fixtures
