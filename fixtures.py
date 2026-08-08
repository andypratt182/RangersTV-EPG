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

FIXTURE_DAYS = 24

LIVE_FALLBACK_MINUTES = 150

TARGET_SEASON = "2026/2027"


# ============================================================
# CONFIRMED SCOTTISH PREMIERSHIP
# ============================================================

KNOWN_PREMIERSHIP_ID = 501

KNOWN_PREMIERSHIP_SEASON_ID = 28275


# ============================================================
# COMPETITION SEARCH TERMS
# ============================================================

SCOTTISH_CUP_NAMES = {

    "scottish cup",
    "scottish fa cup",
    "sfa cup",
    "scottish football association cup"
}


SCOTTISH_LEAGUE_CUP_NAMES = {

    "scottish league cup",
    "league cup",
    "premier sports cup",
    "viaplay cup",
    "betfred cup"
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

        "api_token":
            token
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
        print(
            "SPORTMONKS API ERROR"
        )
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
# NORMALISE NAME
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
# GET CONFIGURED TEAMS
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

        if football_name.endswith(
            " TV"
        ):

            football_name = (
                football_name[:-3]
            )

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
# GET LEAGUES
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

    while True:

        print(
            f"Checking leagues page "
            f"{page}..."
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

        current_page = pagination.get(
            "current_page"
        )

        last_page = pagination.get(
            "last_page"
        )

        has_more = pagination.get(
            "has_more"
        )

        if (
            has_more is False
        ):

            break

        if (
            current_page is not None
            and
            last_page is not None
            and
            current_page >= last_page
        ):

            break

        if (
            has_more is None
            and
            last_page is None
            and
            len(page_data) < 100
        ):

            break

        page += 1

        if page > 50:

            print(
                "Stopping league discovery "
                "after 50 pages."
            )

            break

    # --------------------------------------------------------
    # Remove duplicates.
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
        f"unique competitions."
    )

    return leagues


# ============================================================
# FIND COMPETITION BY NAME
# ============================================================

def find_competition(
    leagues,
    names
):

    wanted = {

        normalise_competition_name(
            name
        )

        for name in names
    }

    # --------------------------------------------------------
    # Exact match first.
    # --------------------------------------------------------

    for league in leagues:

        name = league.get(
            "name",
            ""
        )

        normalised = (
            normalise_competition_name(
                name
            )
        )

        if normalised in wanted:

            return league

    # --------------------------------------------------------
    # Partial match second.
    # --------------------------------------------------------

    for league in leagues:

        name = league.get(
            "name",
            ""
        )

        normalised = (
            normalise_competition_name(
                name
            )
        )

        for search_name in wanted:

            if (
                search_name
                and
                search_name in normalised
            ):

                return league

    return None


# ============================================================
# GET LEAGUE SEASONS
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

    return league.get(
        "seasons",
        []
    )


# ============================================================
# FIND 2026/27 SEASON
# ============================================================

def find_target_season(
    league,
    token,
    display_name
):

    league_id = league.get(
        "id"
    )

    print()
    print("==============================")
    print(
        f"Checking {display_name} season"
    )
    print("==============================")

    print(
        f"League ID: {league_id}"
    )

    seasons = get_league_seasons(
        league_id,
        token
    )

    print(
        f"Found {len(seasons)} season(s)"
    )

    for season in seasons:

        print(
            f"  ID {season.get('id')}: "
            f"{season.get('name')}"
        )

    # --------------------------------------------------------
    # Exact season name.
    # --------------------------------------------------------

    for season in seasons:

        name = str(
            season.get(
                "name",
                ""
            )
        ).strip()

        if name in (
            "2026/2027",
            "2026/27",
            "2026 - 2027",
            "2026-2027"
        ):

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
                f"{name}"
            )

            return season

    # --------------------------------------------------------
    # Flexible season search.
    # --------------------------------------------------------

    for season in seasons:

        name = str(
            season.get(
                "name",
                ""
            )
        )

        if (
            "2026" in name
            and
            "2027" in name
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
                f"{name}"
            )

            return season

    # --------------------------------------------------------
    # Year field fallback.
    # --------------------------------------------------------

    for season in seasons:

        if str(
            season.get("year")
        ) == "2026":

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
        f"{display_name}."
    )

    return None


# ============================================================
# DISCOVER SCOTTISH COMPETITIONS
# ============================================================

def discover_competitions(
    token
):

    leagues = get_all_leagues(
        token
    )

    discovered = {}

    # ========================================================
    # PREMIERSHIP
    # ========================================================

    premiership = find_competition(
        leagues,
        {
            "Scottish Premiership",
            "Premiership"
        }
    )

    if premiership:

        print()
        print(
            "Scottish Premiership "
            "competition found."
        )

        print(
            f"Name: "
            f"{premiership.get('name')}"
        )

        print(
            f"ID: "
            f"{premiership.get('id')}"
        )

        season = find_target_season(

            premiership,

            token,

            "Scottish Premiership"
        )

        if season:

            discovered[
                "premiership"
            ] = {

                "league_id":
                    premiership["id"],

                "season_id":
                    season["id"],

                "name":
                    "Scottish Premiership"
            }

    # --------------------------------------------------------
    # Confirmed fallback.
    # --------------------------------------------------------

    if (
        "premiership"
        not in discovered
    ):

        print()
        print(
            "Using confirmed "
            "Scottish Premiership "
            "fallback."
        )

        discovered[
            "premiership"
        ] = {

            "league_id":
                KNOWN_PREMIERSHIP_ID,

            "season_id":
                KNOWN_PREMIERSHIP_SEASON_ID,

            "name":
                "Scottish Premiership"
        }

    # ========================================================
    # SCOTTISH CUP
    # ========================================================

    print()
    print(
        "Searching for:"
    )

    print(
        "  Scottish Cup"
    )

    scottish_cup = find_competition(
        leagues,
        SCOTTISH_CUP_NAMES
    )

    if scottish_cup:

        print()
        print(
            "SCOTTISH CUP FOUND"
        )

        print(
            f"Name: "
            f"{scottish_cup.get('name')}"
        )

        print(
            f"ID: "
            f"{scottish_cup.get('id')}"
        )

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

    else:

        print()
        print(
            "WARNING: Scottish Cup "
            "was not found in the "
            "Sportmonks leagues endpoint."
        )

    # ========================================================
    # SCOTTISH LEAGUE CUP
    # ========================================================

    print()
    print(
        "Searching for:"
    )

    print(
        "  Scottish League Cup"
    )

    league_cup = find_competition(
        leagues,
        SCOTTISH_LEAGUE_CUP_NAMES
    )

    if league_cup:

        print()
        print(
            "SCOTTISH LEAGUE CUP FOUND"
        )

        print(
            f"Name: "
            f"{league_cup.get('name')}"
        )

        print(
            f"ID: "
            f"{league_cup.get('id')}"
        )

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

    else:

        print()
        print(
            "WARNING: Scottish League Cup "
            "was not found in the "
            "Sportmonks leagues endpoint."
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("==============================")
    print(
        "DISCOVERED SCOTTISH "
        "COMPETITIONS"
    )
    print("==============================")

    for competition in (
        discovered.values()
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
# EXTRACT FIXTURES
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
                value.get("id")
                is not None
                and
                value.get(
                    "starting_at"
                )
                is not None
                and
                "participants"
                in value
            ):

                fixtures.append(
                    value
                )

            for child in (
                value.values()
            ):

                walk(child)

        elif isinstance(
            value,
            list
        ):

            for child in value:

                walk(child)

    walk(data)

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

    print()
    print(
        "=========================================="
    )

    print(
        f"SPORTMONKS "
        f"{competition['name'].upper()} DOWNLOAD"
    )

    print(
        "=========================================="
    )

    print(
        f"League ID: "
        f"{competition['league_id']}"
    )

    print(
        f"Season ID: "
        f"{competition['season_id']}"
    )

    print()

    endpoint = (
        "schedules/seasons/"
        f"{competition['season_id']}"
    )

    print(
        f"Downloading 2026/27 "
        f"{competition['name']} schedule..."
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
        f"for "
        f"{competition['name']}"
    )

    # --------------------------------------------------------
    # Add our own competition label.
    # --------------------------------------------------------

    for event in events:

        event[
            "_epg_competition"
        ] = competition[
            "name"
        ]

    return events


# ============================================================
# DOWNLOAD EVERYTHING
# ============================================================

def download_all_schedules():

    token = os.getenv(
        "SPORTMONKS_API_TOKEN"
    )

    if not token:

        raise RuntimeError(
            "SPORTMONKS_API_TOKEN "
            "environment variable "
            "is not set."
        )

    competitions = (
        discover_competitions(
            token
        )
    )

    all_events = []

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
            print(
                "WARNING: Could not "
                f"download "
                f"{competition['name']}"
            )

            print(
                f"Reason: {e}"
            )

            print(
                "Continuing with "
                "other competitions."
            )

    # --------------------------------------------------------
    # Remove duplicate fixtures.
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
    # Fallback.
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
# BUILD FIXTURES
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
        today
        +
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

        channel_fixtures[
            team["name"]
        ] = []

    # --------------------------------------------------------
    # Process fixtures.
    # --------------------------------------------------------

    for event in events:

        kickoff = parse_kickoff(
            event.get(
                "starting_at"
            )
        )

        if kickoff is None:

            continue

        kickoff_uk = (
            kickoff.astimezone(
                UK_TZ
            )
        )

        status = get_event_status(
            event
        )

        live = is_live_status(
            status
        )

        finished = (
            is_finished_status(
                status
            )
        )

        # ----------------------------------------------------
        # Date range.
        # ----------------------------------------------------

        if (
            kickoff_uk.date()
            <
            start_date
        ):

            continue

        if (
            kickoff_uk.date()
            >
            end_date
        ):

            continue

        # ----------------------------------------------------
        # Completed fixtures.
        # ----------------------------------------------------

        if finished and not live:

            print()
            print(
                f"Skipping completed "
                f"event "
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
                f"Status: "
                f"{status}"
            )

        # ----------------------------------------------------
        # Kick-off passed but no live status.
        # ----------------------------------------------------

        elif kickoff <= now_utc:

            age_minutes = (
                now_utc - kickoff
            ).total_seconds() / 60

            if (
                age_minutes
                >
                LIVE_FALLBACK_MINUTES
            ):

                print()
                print(
                    f"Skipping old fixture "
                    f"{event.get('id')}: "
                    f"{int(age_minutes)} "
                    f"minutes old"
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
        # Teams.
        # ----------------------------------------------------

        home, away = (
            get_participants(
                event
            )
        )

        if not home or not away:

            print()
            print(
                "WARNING: Could not "
                "identify home/away "
                "teams."
            )

            print(
                "Fixture ID:",
                event.get("id")
            )

            continue

        home_key = (
            normalise_team_name(
                home
            )
        )

        away_key = (
            normalise_team_name(
                away
            )
        )

        # ----------------------------------------------------
        # Match every configured club.
        #
        # This allows an Old Firm fixture to appear on both
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
        # Competition.
        # ----------------------------------------------------

        competition = event.get(
            "_epg_competition",
            "Scottish Football"
        )

        # ----------------------------------------------------
        # Stadium.
        # ----------------------------------------------------

        stadium = "Venue TBC"

        venue = event.get(
            "venue"
        )

        if isinstance(
            venue,
            dict
        ):

            venue_name = venue.get(
                "name"
            )

            if venue_name:

                stadium = venue_name

        # ----------------------------------------------------
        # Fall back to configured home stadium.
        # ----------------------------------------------------

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

        for matched_team in (
            matched_teams
        ):

            fixture = {

                "channel":
                    matched_team[
                        "name"
                    ],

                "channel_id":
                    matched_team[
                        "channel_id"
                    ],

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
                matched_team[
                    "name"
                ]
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
                f"Live: "
                f"{live}"
            )

            print(
                f"Fixture ID: "
                f"{event.get('id')}"
            )

    # --------------------------------------------------------
    # Sort each channel.
    # --------------------------------------------------------

    for channel_name in (
        channel_fixtures
    ):

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

                live_marker = (
                    " [LIVE]"
                )

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
# ============================================================

_SCHEDULE_CACHE = None

_FIXTURE_CACHE = None


# ============================================================
# GET FIXTURES
# ============================================================

def get_fixtures(
    team
):

    global _SCHEDULE_CACHE

    global _FIXTURE_CACHE

    # --------------------------------------------------------
    # Download and process only once per generator run.
    # --------------------------------------------------------

    if _FIXTURE_CACHE is None:

        _SCHEDULE_CACHE = (
            download_all_schedules()
        )

        _FIXTURE_CACHE = (
            build_fixtures(
                _SCHEDULE_CACHE
            )
        )

    channel_name = team[
        "name"
    ]

    fixtures = (
        _FIXTURE_CACHE.get(
            channel_name,
            []
        )
    )

    print()
    print("==============================")

    print(
        f"Found {len(fixtures)} "
        f"upcoming/live fixtures "
        f"for {channel_name}"
    )

    print(
        "=============================="
    )

    if not fixtures:

        print(
            f"No upcoming/live "
            f"fixtures for "
            f"{channel_name}"
        )

    return fixtures
