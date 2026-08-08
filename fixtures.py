import os
import requests
import re

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

# Number of days of upcoming fixtures to collect
FIXTURE_DAYS = 24

# How long after scheduled kick-off a match can remain
# in the fixture data when Sportmonks has not supplied
# a recognised live state.
LIVE_FALLBACK_MINUTES = 150

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
    print(
        "Checking Scottish Premiership season"
    )
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

    # --------------------------------------------------------
    # Remove punctuation.
    #
    # This makes:
    #
    # St. Johnstone -> st johnstone
    # St Johnstone  -> st johnstone
    #
    # St. Mirren -> st mirren
    # St Mirren  -> st mirren
    # --------------------------------------------------------

    name = re.sub(
        r"[^\w\s]",
        " ",
        name
    )

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
# EVENT STATUS
# ============================================================

def get_event_status(event):

    """
    Return a normalised Sportmonks event state.

    Sportmonks may expose state information in
    slightly different fields depending on the
    endpoint/version, so several possibilities
    are checked.
    """

    state = event.get(
        "state"
    )

    if isinstance(
        state,
        dict
    ):

        for key in (
            "short_name",
            "name",
            "developer_name"
        ):

            value = state.get(
                key
            )

            if value:

                return str(
                    value
                ).upper()

    # Some responses may expose status directly.

    status = event.get(
        "status"
    )

    if isinstance(
        status,
        dict
    ):

        for key in (
            "short_name",
            "name",
            "developer_name"
        ):

            value = status.get(
                key
            )

            if value:

                return str(
                    value
                ).upper()

    elif status:

        return str(
            status
        ).upper()

    return ""


# ============================================================
# DETERMINE WHETHER MATCH IS LIVE
# ============================================================

def is_live_status(status):

    if not status:

        return False

    live_states = {

        "LIVE",
        "HT",
        "BREAK",
        "ET",
        "AET",
        "PEN",
        "PENALTIES",
        "1H",
        "2H",
        "EXTRA_TIME"
    }

    return status in live_states


# ============================================================
# DETERMINE WHETHER MATCH IS FINISHED
# ============================================================

def is_finished_status(status):

    if not status:

        return False

    finished_states = {

        "FT",
        "AET",
        "AP",
        "AFTER_PENALTIES",
        "FINISHED",
        "POSTPONED",
        "CANCELLED",
        "CANCELED",
        "ABANDONED"
    }

    return status in finished_states


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
    print(
        "SPORTMONKS SCOTTISH PREMIERSHIP DOWNLOAD"
    )
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

    now_uk = now_utc.astimezone(
        UK_TZ
    )

    today = now_uk.date()

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Start with TODAY, not tomorrow.
    #
    # This allows a fixture currently being played to
    # reach the XMLTV generator.
    # --------------------------------------------------------

    start_date = today

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

    print(
        f"Current UK time: "
        f"{now_uk.strftime('%Y-%m-%d %H:%M:%S')}"
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
            f"-> Sportmonks match name key: "
            f"'{key}'"
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

        status = get_event_status(
            event
        )

        live = is_live_status(
            status
        )

        finished = is_finished_status(
            status
        )

        # ----------------------------------------------------
        # Date window
        # ----------------------------------------------------

        if kickoff_uk.date() < start_date:

            continue

        if kickoff_uk.date() > end_date:

            continue

        # ----------------------------------------------------
        # Finished/cancelled/postponed matches
        # ----------------------------------------------------

        if finished and not live:

            print()
            print(
                f"Skipping completed event "
                f"{event.get('id')}: "
                f"{status}"
            )

            continue

        # ----------------------------------------------------
        # If Sportmonks says the match is live, ALWAYS keep it.
        # ----------------------------------------------------

        if live:

            print()
            print(
                "LIVE FIXTURE DETECTED"
            )

            print(
                "---------------"
            )

            print(
                f"Fixture ID: "
                f"{event.get('id')}"
            )

            print(
                f"Status: {status}"
            )

        # ----------------------------------------------------
        # If the kickoff has passed but Sportmonks has not
        # supplied a recognised live/finished status, keep it
        # for a limited period.
        #
        # This is important because API status updates can
        # occasionally lag behind the scheduled kick-off.
        # ----------------------------------------------------

        elif kickoff <= now_utc:

            age_minutes = (
                now_utc - kickoff
            ).total_seconds() / 60

            if (
                age_minutes >
                LIVE_FALLBACK_MINUTES
            ):

                print()
                print(
                    f"Skipping old fixture "
                    f"{event.get('id')}: "
                    f"{int(age_minutes)} minutes old"
                )

                continue

            print()
            print(
                "LIVE FALLBACK FIXTURE"
            )

            print(
                "---------------"
            )

            print(
                f"Fixture ID: "
                f"{event.get('id')}"
            )

            print(
                f"No recognised live status."
            )

            print(
                f"Kick-off was "
                f"{int(age_minutes)} minutes ago."
            )

        # ----------------------------------------------------
        # Get home and away teams
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
        # Find ALL configured clubs involved.
        #
        # This deliberately allows an Old Firm match to appear
        # on BOTH Rangers TV and Celtic TV.
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
        # FIXTURE STADIUM
        #
        # Stadium belongs to the fixture, not the channel.
        #
        # Therefore:
        #
        # Rangers vs Hibernian
        # -> Ibrox Stadium
        #
        # Both Rangers TV AND Hibernian TV receive
        # Ibrox Stadium.
        #
        # Hibernian vs Rangers
        # -> Easter Road
        #
        # Both channels receive Easter Road.
        # ----------------------------------------------------

        home_team = allowed_teams.get(
            home_key
        )

        if home_team:

            stadium = home_team[
                "stadium"
            ]

        else:

            stadium = "Venue TBC"

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
        # Add fixture to EVERY relevant channel.
        # ----------------------------------------------------

        for matched_team in matched_teams:

            fixture = {

                "channel":
                    matched_team["name"],

                "channel_id":
                    matched_team["channel_id"],

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
                    "",

                # Extra information is included
                # without changing the existing
                # fields used by xmltv.py.

                "fixture_id":
                    event.get(
                        "id"
                    ),

                "status":
                    status,

                "live":
                    live
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
                f"Sportmonks status: "
                f"{status or 'UNKNOWN'}"
            )

            print(
                f"Live: "
                f"{live}"
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

    # --------------------------------------------------------
    # Diagnostic summary
    # --------------------------------------------------------

    print()
    print("==============================")
    print("FIXTURE SUMMARY")
    print("==============================")

    for channel_name, fixtures in (
        channel_fixtures.items()
    ):

        print(
            f"{channel_name}: "
            f"{len(fixtures)} fixture(s)"
        )

        for fixture in fixtures:

            live_marker = ""

            if fixture.get(
                "live"
            ):

                live_marker = " [LIVE]"

            print(
                f"  {fixture['kickoff']} - "
                f"{fixture['home']} vs "
                f"{fixture['away']}"
                f"{live_marker}"
            )

    return channel_fixtures


# ============================================================
# CACHE
#
# Sportmonks is downloaded and processed only once during
# each generator.py run.
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
        f"upcoming/live fixtures for "
        f"{channel_name}"
    )

    print(
        "=============================="
    )

    if not fixtures:

        print(
            f"No upcoming/live fixtures for "
            f"{channel_name}"
        )

    return fixtures
