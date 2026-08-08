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
# SETTINGS
# ============================================================

# Number of days of upcoming fixtures to collect.
FIXTURE_DAYS = 24

# How long after scheduled kick-off a match can remain
# in the fixture data when Sportmonks has not supplied
# a recognised live state.
LIVE_FALLBACK_MINUTES = 150

# Season we want.
TARGET_SEASON = "2026/27"


# ============================================================
# KNOWN PREMIERSHIP FALLBACK
# ============================================================
#
# These are already confirmed from your working setup.
#
# The cups are NOT hard-coded.
# They are discovered automatically below.
#
# ============================================================

KNOWN_PREMIERSHIP_ID = 501
KNOWN_PREMIERSHIP_SEASON_ID = 28275


# ============================================================
# COMPETITION SEARCH NAMES
# ============================================================
#
# Sportmonks may use slightly different names for competitions.
#
# We therefore search using several possible names.
#
# ============================================================

COMPETITION_SEARCHES = {

    "scottish_premiership": {

        "display_name":
            "Scottish Premiership",

        "names": [

            "Scottish Premiership",

            "Premiership",

            "Scottish Premier"
        ]
    },

    "scottish_cup": {

        "display_name":
            "Scottish Cup",

        "names": [

            "Scottish Cup",

            "Scottish Football Association Cup",

            "Scottish FA Cup",

            "SFA Cup"
        ]
    },

    "scottish_league_cup": {

        "display_name":
            "Scottish League Cup",

        "names": [

            "Scottish League Cup",

            "League Cup",

            "Scottish League Cup",

            "Premier Sports Cup",

            "Viaplay Cup",

            "Betfred Cup",

            "Cinch Premiership Cup"
        ]
    }
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
# NORMALISE COMPETITION NAME
# ============================================================

def normalise_competition_name(
    name
):

    if not name:

        return ""

    name = str(
        name
    ).lower().strip()

    name = re.sub(
        r"[^\w\s]",
        " ",
        name
    )

    return " ".join(
        name.split()
    )


# ============================================================
# NORMALISE TEAM NAME
# ============================================================

def normalise_team_name(
    name
):

    if not name:

        return ""

    name = name.lower().strip()

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
# GET ALL SPORTMONKS LEAGUES
# ============================================================
#
# We deliberately discover competitions rather than assuming
# their IDs.
#
# Sportmonks paginates the leagues endpoint, so we continue
# through available pages.
#
# ============================================================

def get_all_leagues(
    token
):

    print()
    print("==============================")
    print(
        "DISCOVERING SPORTMONKS "
        "COMPETITIONS"
    )
    print("==============================")

    leagues = []

    page = 1

    max_pages = 20

    while page <= max_pages:

        print(
            f"Checking leagues page {page}..."
        )

        data = sportmonks_get(
            "leagues",
            token,
            {
                "page":
                    page,

                "per_page":
                    100
            }
        )

        page_data = data.get(
            "data",
            []
        )

        if not page_data:

            break

        leagues.extend(
            page_data
        )

        pagination = data.get(
            "pagination",
            {}
        )

        has_more = pagination.get(
            "has_more"
        )

        if has_more is False:

            break

        # ----------------------------------------------------
        # Some Sportmonks responses expose current/last page
        # instead of has_more.
        # ----------------------------------------------------

        last_page = pagination.get(
            "last_page"
        )

        current_page = pagination.get(
            "current_page"
        )

        if (
            last_page is not None
            and
            current_page is not None
            and
            current_page >= last_page
        ):

            break

        # Safety check.
        #
        # If pagination information isn't available and we
        # received fewer than 100 results, assume this is the
        # final page.
        # ----------------------------------------------------

        if (
            not has_more
            and
            last_page is None
            and
            len(page_data) < 100
        ):

            break

        page += 1

    # --------------------------------------------------------
    # Remove duplicate league IDs.
    # --------------------------------------------------------

    unique = {}

    for league in leagues:

        league_id = league.get(
            "id"
        )

        if league_id is not None:

            unique[
                league_id
            ] = league

    leagues = list(
        unique.values()
    )

    print()
    print(
        f"Discovered {len(leagues)} "
        f"unique Sportmonks competitions."
    )

    return leagues


# ============================================================
# FIND TARGET COMPETITION
# ============================================================

def find_competition(
    leagues,
    competition_key
):

    config = COMPETITION_SEARCHES[
        competition_key
    ]

    wanted_names = [
        normalise_competition_name(
            name
        )
        for name in config[
            "names"
        ]
    ]

    print()
    print(
        "Searching for:"
    )

    print(
        f"  {config['display_name']}"
    )

    # --------------------------------------------------------
    # First attempt: exact name match.
    # --------------------------------------------------------

    for league in leagues:

        league_name = league.get(
            "name",
            ""
        )

        normalised = (
            normalise_competition_name(
                league_name
            )
        )

        if normalised in wanted_names:

            print()
            print(
                "COMPETITION FOUND"
            )

            print(
                "---------------"
            )

            print(
                f"Name: {league_name}"
            )

            print(
                f"ID: "
                f"{league.get('id')}"
            )

            return league

    # --------------------------------------------------------
    # Second attempt: contains match.
    #
    # This handles names such as:
    #
    # "Scottish League Cup"
    # "Scottish League Cup 2026"
    #
    # --------------------------------------------------------

    for league in leagues:

        league_name = league.get(
            "name",
            ""
        )

        normalised = (
            normalise_competition_name(
                league_name
            )
        )

        for wanted in wanted_names:

            if (
                wanted
                and
                wanted in normalised
            ):

                print()
                print(
                    "COMPETITION FOUND "
                    "(PARTIAL MATCH)"
                )

                print(
                    "---------------"
                )

                print(
                    f"Name: {league_name}"
                )

                print(
                    f"ID: "
                    f"{league.get('id')}"
                )

                return league

    print()
    print(
        f"WARNING: Could not discover "
        f"{config['display_name']}."
    )

    return None


# ============================================================
# GET SEASONS FOR LEAGUE
# ============================================================

def get_league_seasons(
    league_id,
    token
):

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

    return (
        league.get(
            "seasons",
            []
        )
    )


# ============================================================
# FIND 2026/27 SEASON
# ============================================================

def find_target_season(
    league,
    token,
    competition_name
):

    league_id = league.get(
        "id"
    )

    print()
    print(
        f"Checking {competition_name} "
        f"season"
    )

    print(
        f"League ID: {league_id}"
    )

    seasons = get_league_seasons(
        league_id,
        token
    )

    print(
        f"Found {len(seasons)} "
        f"season(s)"
    )

    # --------------------------------------------------------
    # Display available seasons.
    # --------------------------------------------------------

    for season in seasons:

        print(
            f"  ID {season.get('id')}: "
            f"{season.get('name')}"
        )

    # --------------------------------------------------------
    # Look for 2026/27.
    # --------------------------------------------------------

    target_strings = {

        "2026/27",
        "2026/2027",
        "2026 - 2027",
        "2026-2027"
    }

    for season in seasons:

        season_name = str(
            season.get(
                "name",
                ""
            )
        ).strip()

        if season_name in target_strings:

            print()
            print(
                "TARGET SEASON FOUND"
            )

            print(
                f"  ID: "
                f"{season.get('id')}"
            )

            print(
                f"  Name: "
                f"{season_name}"
            )

            return season

    # --------------------------------------------------------
    # More flexible search.
    # --------------------------------------------------------

    for season in seasons:

        season_name = str(
            season.get(
                "name",
                ""
            )
        )

        if (
            "2026"
            in season_name
            and
            (
                "2027"
                in season_name
                or
                "26/27"
                in season_name
            )
        ):

            print()
            print(
                "TARGET SEASON FOUND "
                "(FLEXIBLE MATCH)"
            )

            print(
                f"  ID: "
                f"{season.get('id')}"
            )

            print(
                f"  Name: "
                f"{season_name}"
            )

            return season

    # --------------------------------------------------------
    # Check year field.
    # --------------------------------------------------------

    for season in seasons:

        year = season.get(
            "year"
        )

        if str(year) == "2026":

            print()
            print(
                "TARGET SEASON FOUND "
                "(YEAR MATCH)"
            )

            print(
                f"  ID: "
                f"{season.get('id')}"
            )

            print(
                f"  Name: "
                f"{season.get('name')}"
            )

            return season

    print()
    print(
        f"WARNING: Could not find "
        f"2026/27 season for "
        f"{competition_name}."
    )

    return None


# ============================================================
# DISCOVER ALL SCOTTISH COMPETITIONS
# ============================================================

def discover_competitions(
    token
):

    leagues = get_all_leagues(
        token
    )

    discovered = {}

    # --------------------------------------------------------
    # Discover Premiership.
    # --------------------------------------------------------

    premiership = find_competition(
        leagues,
        "scottish_premiership"
    )

    if premiership:

        season = find_target_season(
            premiership,
            token,
            "Scottish Premiership"
        )

        if season:

            discovered[
                "scottish_premiership"
            ] = {

                "league_id":
                    premiership["id"],

                "season_id":
                    season["id"],

                "name":
                    "Scottish Premiership"
            }

    # --------------------------------------------------------
    # Known Premiership fallback.
    #
    # This protects the working configuration you already
    # have if the league discovery endpoint behaves differently.
    # --------------------------------------------------------

    if (
        "scottish_premiership"
        not in discovered
    ):

        print()
        print(
            "Using confirmed Scottish "
            "Premiership fallback."
        )

        discovered[
            "scottish_premiership"
        ] = {

            "league_id":
                KNOWN_PREMIERSHIP_ID,

            "season_id":
                KNOWN_PREMIERSHIP_SEASON_ID,

            "name":
                "Scottish Premiership"
        }

    # --------------------------------------------------------
    # Discover Scottish Cup.
    # --------------------------------------------------------

    scottish_cup = find_competition(
        leagues,
        "scottish_cup"
    )

    if scottish_cup:

        season = find_target_season(
            scottish_cup,
            token,
            "Scottish Cup"
        )

        if season:

            discovered[
                "scottish_cup"
            ] = {

                "league_id":
                    scottish_cup["id"],

                "season_id":
                    season["id"],

                "name":
                    "Scottish Cup"
            }

    # --------------------------------------------------------
    # Discover Scottish League Cup.
    # --------------------------------------------------------

    league_cup = find_competition(
        leagues,
        "scottish_league_cup"
    )

    if league_cup:

        season = find_target_season(
            league_cup,
            token,
            "Scottish League Cup"
        )

        if season:

            discovered[
                "scottish_league_cup"
            ] = {

                "league_id":
                    league_cup["id"],

                "season_id":
                    season["id"],

                "name":
                    "Scottish League Cup"
            }

    # --------------------------------------------------------
    # Summary.
    # --------------------------------------------------------

    print()
    print("==============================")
    print(
        "DISCOVERED SCOTTISH "
        "COMPETITIONS"
    )
    print("==============================")

    for key, competition in (
        discovered.items()
    ):

        print(
            f"{competition['name']}"
        )

        print(
            f"  League ID: "
            f"{competition['league_id']}"
        )

        print(
            f"  Season ID: "
            f"{competition['season_id']}"
        )

    return discovered


# ============================================================
# EXTRACT FIXTURES FROM SCHEDULE
# ============================================================

def extract_schedule_fixtures(
    data
):

    fixtures = []

    def walk(value):

        if isinstance(
            value,
            dict
        ):

            if (
                value.get("id") is not None
                and
                value.get(
                    "starting_at"
                ) is not None
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

    season_id = competition[
        "season_id"
    ]

    print()
    print("==========================================")
    print(
        f"SPORTMONKS "
        f"{competition_name.upper()} DOWNLOAD"
    )
    print("==========================================")

    print(
        f"League ID: "
        f"{competition['league_id']}"
    )

    print(
        f"Season ID: "
        f"{season_id}"
    )

    print()
    print(
        f"Downloading 2026/27 "
        f"{competition_name} schedule..."
    )

    endpoint = (
        f"schedules/seasons/"
        f"{season_id}"
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

    # --------------------------------------------------------
    # Attach EPG competition information.
    # --------------------------------------------------------

    for event in events:

        event[
            "_epg_competition"
        ] = competition_name

        event[
            "_epg_league_id"
        ] = competition[
            "league_id"
        ]

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

    # --------------------------------------------------------
    # Automatically discover competitions.
    # --------------------------------------------------------

    competitions = discover_competitions(
        token
    )

    all_events = []

    # --------------------------------------------------------
    # Download each discovered competition.
    # --------------------------------------------------------

    for competition in (
        competitions.values()
    ):

        try:

            events = (
                download_competition_schedule(
                    competition,
                    token
                )
            )

            all_events.extend(
                events
            )

        except Exception as e:

            print()
            print("==============================")
            print(
                "WARNING: COMPETITION "
                "DOWNLOAD FAILED"
            )

            print(
                f"Competition: "
                f"{competition['name']}"
            )

            print(
                f"Reason: {e}"
            )

            print(
                "Continuing with the "
                "remaining competitions."
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
# EVENT STATUS
# ============================================================

def get_event_status(
    event
):

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
# LIVE STATUS
# ============================================================

def is_live_status(
    status
):

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
# FINISHED STATUS
# ============================================================

def is_finished_status(
    status
):

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
# PROCESS COMPLETE SCHEDULE
# ============================================================

def build_fixtures(
    events
):

    now_utc = datetime.now(
        timezone.utc
    )

    now_uk = now_utc.astimezone(
        UK_TZ
    )

    today = now_uk.date()

    start_date = today

    end_date = (
        today +
        timedelta(
            days=FIXTURE_DAYS
        )
    )

    print()
    print("==============================")
    print(
        "Sportmonks fixture window"
    )
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
    # Empty fixture list for every channel.
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
    # Process each Sportmonks fixture.
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
        # Completed/cancelled/postponed.
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
        # Live fixture.
        # ----------------------------------------------------

        if live:

            print()
            print(
                "LIVE FIXTURE DETECTED"
            )

            print(
                f"Fixture ID: "
                f"{event.get('id')}"
            )

            print(
                f"Status: {status}"
            )

        # ----------------------------------------------------
        # Kick-off has passed but Sportmonks hasn't supplied
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
                f"Fixture ID: "
                f"{event.get('id')}"
            )

            print(
                f"Kick-off was "
                f"{int(age_minutes)} "
                f"minutes ago."
            )

        # ----------------------------------------------------
        # Participants.
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
        # Find all configured clubs involved.
        #
        # Old Firm matches therefore appear on both channels.
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
        # Competition.
        # ----------------------------------------------------

        competition = event.get(
            "_epg_competition",
            "Scottish Football"
        )

        # ----------------------------------------------------
        # Stadium.
        #
        # Prefer Sportmonks venue information.
        # Otherwise use the configured home club stadium.
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
        # Add to every relevant channel.
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
    # Sort chronologically.
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
# PARSE KICKOFF
# ============================================================

def parse_kickoff(
    value
):

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

def get_participants(
    event
):

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
# GET FIXTURES
# ============================================================

_SCHEDULE_CACHE = None

_FIXTURE_CACHE = None


def get_fixtures(
    team
):

    global _SCHEDULE_CACHE
    global _FIXTURE_CACHE

    # --------------------------------------------------------
    # Download/process everything only once per generator run.
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
