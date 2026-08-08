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


# ============================================================
# FIXTURE SETTINGS
# ============================================================

# Number of days of upcoming fixtures to collect.
FIXTURE_DAYS = 24


# How long after scheduled kick-off a match can remain
# in the fixture data when Sportmonks has not supplied
# a recognised live state.
LIVE_FALLBACK_MINUTES = 150


# ============================================================
# SCOTTISH COMPETITIONS
# ============================================================
#
# Sportmonks league IDs:
#
# 501 = Scottish Premiership
#
# The cup IDs are configurable here so they are easy to
# change if Sportmonks changes its competition structure.
#
# ============================================================

COMPETITIONS = {

    "scottish_premiership": {

        "league_id": 501,

        "name":
            "Scottish Premiership",
    },

    "scottish_cup": {

        "league_id": 507,

        "name":
            "Scottish Cup",
    },

    "scottish_league_cup": {

        "league_id": 510,

        "name":
            "Scottish League Cup",
    },
}


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
            "Accept":
                "application/json"
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
# FIND 2026/27 SEASON
# ============================================================

def get_2026_27_season(
    league_id,
    token,
    competition_name
):

    print()
    print("==============================")
    print(
        f"Checking {competition_name} season"
    )
    print("==============================")

    print(
        f"League ID: {league_id}"
    )

    data = sportmonks_get(
        f"leagues/{league_id}",
        token,
        {
            "include":
                "seasons"
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

    # --------------------------------------------------------
    # Look for 2026/27 by season name.
    # --------------------------------------------------------

    for season in seasons:

        season_name = str(
            season.get(
                "name",
                ""
            )
        )

        if (
            "2026/27"
            in season_name
            or
            "2026/2027"
            in season_name
        ):

            print(
                f"Confirmed season: "
                f"{season.get('id')} "
                f"({season_name})"
            )

            return season

    # --------------------------------------------------------
    # Some Sportmonks responses may expose a year field.
    # --------------------------------------------------------

    for season in seasons:

        year = season.get(
            "year"
        )

        if str(year) in (
            "2026",
            "2026/27",
            "2026/2027"
        ):

            print(
                f"Confirmed season: "
                f"{season.get('id')} "
                f"({season.get('name')})"
            )

            return season

    # --------------------------------------------------------
    # No matching season found.
    # --------------------------------------------------------

    print()
    print(
        f"WARNING: Could not find "
        f"2026/27 {competition_name} season."
    )

    print(
        "Available seasons:"
    )

    for season in seasons:

        print(
            f"  ID {season.get('id')}: "
            f"{season.get('name')}"
        )

    raise RuntimeError(
        f"Could not find 2026/27 season "
        f"for {competition_name} "
        f"(league {league_id})."
    )


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
    # St. Johnstone -> st johnstone
    # St Johnstone  -> st johnstone
    # --------------------------------------------------------

    name = re.sub(
        r"[^\w\s]",
        " ",
        name
    )

    # --------------------------------------------------------
    # Remove common suffixes.
    # --------------------------------------------------------

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

    for channel_id, team in (
        SPFL_TEAMS.items()
    ):

        channel_name = team[
            "name"
        ]

        football_name = channel_name

        # ----------------------------------------------------
        # Remove " TV" from channel names.
        #
        # Rangers TV -> Rangers
        # Celtic TV  -> Celtic
        # ----------------------------------------------------

        if football_name.endswith(
            " TV"
        ):

            football_name = football_name[
                :-3
            ]

        normalised = (
            normalise_team_name(
                football_name
            )
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

    # --------------------------------------------------------
    # Fallback if location metadata isn't available.
    # --------------------------------------------------------

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
    endpoint/version.
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
                and
                value.get("starting_at") is not None
                and
                "participants" in value
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

    # --------------------------------------------------------
    # Remove duplicate fixture IDs.
    # --------------------------------------------------------

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
# DOWNLOAD ONE COMPETITION
# ============================================================

def download_competition_schedule(
    competition,
    token
):

    competition_name = competition[
        "name"
    ]

    league_id = competition[
        "league_id"
    ]

    print()
    print("==========================================")
    print(
        f"SPORTMONKS {competition_name.upper()} DOWNLOAD"
    )
    print("==========================================")

    season = get_2026_27_season(
        league_id,
        token,
        competition_name
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
        f"Downloading 2026/27 "
        f"{competition_name} schedule..."
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
        f"{len(events)} fixture(s) "
        f"for {competition_name}"
    )

    return events


# ============================================================
# DOWNLOAD ALL SCOTTISH COMPETITIONS
# ============================================================

def download_all_schedules():

    token = os.getenv(
        "SPORTMONKS_API_TOKEN"
    )

    if not token:

        raise RuntimeError(
            "SPORTMONKS_API_TOKEN environment "
            "variable is not set."
        )

    all_events = []

    for competition in (
        COMPETITIONS.values()
    ):

        try:

            events = (
                download_competition_schedule(
                    competition,
                    token
                )
            )

        except Exception as e:

            # ------------------------------------------------
            # Don't allow one unavailable competition to
            # destroy the entire EPG.
            #
            # This is particularly useful if the Sportmonks
            # plan does not include one of the cup competitions.
            # ------------------------------------------------

            print()
            print(
                "WARNING: Could not download "
                f"{competition['name']}"
            )

            print(
                f"Reason: {e}"
            )

            print(
                "Continuing with the other "
                "Scottish competitions."
            )

            continue

        # ----------------------------------------------------
        # Store the competition name with every event.
        # ----------------------------------------------------

        for event in events:

            event[
                "_epg_competition"
            ] = competition[
                "name"
            ]

            event[
                "_epg_league_id"
            ] = competition[
                "league_id"
            ]

            all_events.append(
                event
            )

    # --------------------------------------------------------
    # Remove duplicate fixture IDs.
    # --------------------------------------------------------

    unique = {}

    for event in all_events:

        fixture_id = event.get(
            "id"
        )

        if fixture_id is not None:

            unique[
                fixture_id
            ] = event

    events = list(
        unique.values()
    )

    print()
    print("==============================")
    print(
        "TOTAL SCOTTISH FIXTURES"
    )
    print("==============================")

    print(
        f"Total unique fixtures: "
        f"{len(events)}"
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
    # Start today so a currently live match can be included.
    # --------------------------------------------------------

    start_date = today

    end_date = (
        today +
        timedelta(
            days=FIXTURE_DAYS
        )
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

    for key, value in (
        allowed_teams.items()
    ):

        print(
            f"  {value['name']} "
            f"-> '{key}'"
        )

    # --------------------------------------------------------
    # Empty fixture list for every configured channel.
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
    # Process every fixture.
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
        # Date window.
        # ----------------------------------------------------

        if kickoff_uk.date() < start_date:

            continue

        if kickoff_uk.date() > end_date:

            continue

        # ----------------------------------------------------
        # Completed/cancelled/postponed fixtures.
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
        # Recognised live fixture.
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
        # Kick-off has passed but Sportmonks has not supplied
        # a recognised live state.
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
                "No recognised live status."
            )

            print(
                f"Kick-off was "
                f"{int(age_minutes)} "
                f"minutes ago."
            )

        # ----------------------------------------------------
        # Get teams.
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
        # Match the fixture against configured SPFL channels.
        #
        # If Rangers play Celtic, the fixture is added to both
        # Rangers TV and Celtic TV.
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
        # Competition name.
        # ----------------------------------------------------

        competition = event.get(
            "_epg_competition",
            "Scottish Football"
        )

        # ----------------------------------------------------
        # Stadium.
        #
        # First try Sportmonks venue information.
        # If unavailable, use the configured home club stadium.
        # ----------------------------------------------------

        stadium = "Venue TBC"

        venue = event.get(
            "venue"
        )

        if isinstance(
            venue,
            dict
        ):

            stadium = (
                venue.get(
                    "name"
                )
                or
                stadium
            )

        if (
            stadium == "Venue TBC"
            and
            home_key in allowed_teams
        ):

            stadium = allowed_teams[
                home_key
            ][
                "stadium"
            ]

        # ----------------------------------------------------
        # Add fixture to every relevant channel.
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
            # Diagnostic output.
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
                f"Competition: "
                f"{competition}"
            )

            print(
                f"Match: "
                f"{home} vs {away}"
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
                f"Live: {live}"
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
    # Summary.
    # --------------------------------------------------------

    print()
    print("==============================")
    print(
        "FIXTURE SUMMARY"
    )
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
                f"{fixture['away']} - "
                f"{fixture['competition']}"
                f"{live_marker}"
            )

    return channel_fixtures


# ============================================================
# CACHE
#
# All Scottish competitions are downloaded once per
# generator.py run.
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
    # Download and process all competitions once.
    # --------------------------------------------------------

    if _FIXTURE_CACHE is None:

        _SCHEDULE_CACHE = (
            download_all_schedules()
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
