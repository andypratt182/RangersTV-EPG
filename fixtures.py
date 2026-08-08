import requests

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup


BBC_TEAM_URL = (
    "https://www.bbc.co.uk/sport/football/teams/"
    "{slug}/scores-fixtures/{month}"
)

UK_TZ = ZoneInfo("Europe/London")


def get_month_url(team, date):

    """
    Build the BBC monthly fixture-page URL.

    Example:
    https://www.bbc.co.uk/sport/football/teams/rangers/scores-fixtures/2026-08
    """

    urn = team["urn"]

    slug = urn.split(":")[-1]

    return BBC_TEAM_URL.format(
        slug=slug,
        month=date.strftime("%Y-%m")
    )


def parse_fixture_date(date_text, year, month):

    """
    Convert BBC date text into a date.

    This function accepts common BBC formats such as:

        Saturday 8 August
        Sunday 9th August
        Monday 10 August

    """

    cleaned = (
        date_text
        .replace("st", "")
        .replace("nd", "")
        .replace("rd", "")
        .replace("th", "")
    )

    cleaned = " ".join(
        cleaned.split()
    )

    formats = [
        "%A %d %B",
        "%A %d %B %Y",
        "%d %B",
        "%d %B %Y",
    ]

    for fmt in formats:

        try:

            parsed = datetime.strptime(
                cleaned,
                fmt
            )

            return parsed.replace(
                year=year
            ).date()

        except ValueError:
            continue

    return None


def parse_time(time_text):

    """
    Convert a BBC time such as:

        15:00
        19:45

    into a time object.
    """

    try:

        return datetime.strptime(
            time_text.strip(),
            "%H:%M"
        ).time()

    except ValueError:

        return None


def clean_team_name(name):

    """
    Clean BBC team names while keeping the
    actual team name intact.
    """

    if not name:
        return ""

    return " ".join(
        name.split()
    ).strip()


def extract_fixtures_from_page(
    html,
    team,
    target_start,
    target_end
):

    """
    Extract fixtures from one BBC monthly
    team fixture page.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    fixtures = []

    current_date = None
    current_competition = "Football"

    # ---------------------------------------------------------
    # BBC pages are rendered with headings followed by
    # fixture information. We walk through the page text
    # and identify dates, competitions and match blocks.
    # ---------------------------------------------------------

    elements = soup.find_all(
        [
            "h2",
            "h3",
            "h4",
            "time",
            "article",
            "li",
        ]
    )

    for element in elements:

        text = " ".join(
            element.stripped_strings
        )

        if not text:
            continue


        # -----------------------------------------------------
        # Competition headings
        # -----------------------------------------------------

        if (
            "Scottish Premiership" in text
            or "Scottish Cup" in text
            or "League Cup" in text
            or "Champions League" in text
            or "Europa League" in text
            or "Conference League" in text
        ):

            current_competition = text.strip()


        # -----------------------------------------------------
        # Date headings
        # -----------------------------------------------------

        possible_date = parse_fixture_date(
            text,
            target_start.year,
            target_start.month
        )

        if possible_date:

            current_date = possible_date


        # -----------------------------------------------------
        # Look for fixture information
        # -----------------------------------------------------

        if not current_date:
            continue

        if current_date < target_start:
            continue

        if current_date > target_end:
            continue


        # Look for a time in the element
        time_element = element.find(
            "time"
        )

        if time_element:

            time_text = (
                time_element.get_text(
                    strip=True
                )
            )

        else:

            time_text = ""


        kickoff_time = None


        # Try to find HH:MM in the text

        import re

        time_match = re.search(
            r"\b([01]?\d|2[0-3]):[0-5]\d\b",
            text
        )

        if time_match:

            kickoff_time = parse_time(
                time_match.group(0)
            )


        if not kickoff_time:
            continue


        # -----------------------------------------------------
        # Identify teams
        # -----------------------------------------------------

        # BBC commonly exposes team names through
        # links containing /sport/football/teams/
        team_links = element.find_all(
            "a"
        )

        names = []

        for link in team_links:

            link_text = clean_team_name(
                link.get_text(
                    " ",
                    strip=True
                )
            )

            if not link_text:
                continue

            if (
                link_text.lower()
                in {
                    "scores & fixtures",
                    "table",
                    "results",
                }
            ):
                continue

            names.append(
                link_text
            )


        # Remove duplicates while preserving order

        unique_names = []

        for name in names:

            if name not in unique_names:

                unique_names.append(
                    name
                )


        if len(unique_names) < 2:
            continue


        home = unique_names[0]
        away = unique_names[1]


        # -----------------------------------------------------
        # Create UTC kickoff datetime
        # -----------------------------------------------------

        kickoff_local = datetime.combine(
            current_date,
            kickoff_time
        ).replace(
            tzinfo=UK_TZ
        )

        kickoff_utc = kickoff_local.astimezone(
            timezone.utc
        )


        # Ignore fixtures already played

        if kickoff_utc <= datetime.now(
            timezone.utc
        ):
            continue


        fixtures.append(
            {
                "channel": team["name"],

                "channel_id": None,

                "home": home,

                "away": away,

                "competition":
                    current_competition,

                "stadium":
                    team["stadium"],

                "kickoff":
                    kickoff_utc.strftime(
                        "%Y%m%d%H%M%S +0000"
                    ),

                "tv": "",
            }
        )


    return fixtures


def get_fixtures(team):

    """
    Get upcoming fixtures for one SPFL team
    from the BBC Sport team fixture pages.

    Returns the same dictionary structure as
    the previous JSON implementation.
    """

    today = datetime.now(
        UK_TZ
    ).date()


    start_date = (
        today +
        timedelta(days=1)
    )


    end_date = (
        today +
        timedelta(days=24)
    )


    headers = {
        "User-Agent":
            "SPFL-EPG/1.0 "
            "(https://github.com/andypratt182/SPFL-EPG)",

        "Accept":
            "text/html,application/xhtml+xml",
    }


    fixtures = []


    # ---------------------------------------------------------
    # We may cross into the next month, so request both
    # monthly pages when necessary.
    # ---------------------------------------------------------

    months = {
        start_date.replace(day=1),
        end_date.replace(day=1),
    }


    for month_start in sorted(months):

        url = get_month_url(
            team,
            month_start
        )


        print(
            f"Requesting BBC fixture page: "
            f"{url}"
        )


        try:

            response = requests.get(
                url,
                headers=headers,
                timeout=20
            )


        except requests.RequestException as e:

            print(
                f"BBC request failed for "
                f"{team['name']}: {e}"
            )

            continue


        if not response.ok:

            print(
                f"BBC fixture page failed for "
                f"{team['name']}"
            )

            print(
                "Status:",
                response.status_code
            )

            print(
                "URL:",
                response.url
            )

            continue


        month_fixtures = (
            extract_fixtures_from_page(
                response.text,
                team,
                start_date,
                end_date
            )
        )


        fixtures.extend(
            month_fixtures
        )


    # ---------------------------------------------------------
    # Remove duplicate fixtures
    # ---------------------------------------------------------

    unique = {}

    for fixture in fixtures:

        key = (
            fixture["kickoff"],
            fixture["home"],
            fixture["away"]
        )

        unique[key] = fixture


    fixtures = list(
        unique.values()
    )


    # ---------------------------------------------------------
    # Sort chronologically
    # ---------------------------------------------------------

    fixtures.sort(
        key=lambda x: x["kickoff"]
    )


    print(
        f"Found {len(fixtures)} upcoming "
        f"fixtures for {team['name']}"
    )


    return fixtures
