from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET


CHANNEL_ID = "rangerstv"

UK_TZ = ZoneInfo("Europe/London")


def add_programme(
    tv,
    start,
    stop,
    title,
    description
):

    programme = ET.SubElement(
        tv,
        "programme",
        {
            "start": start,
            "stop": stop,
            "channel": CHANNEL_ID,
        },
    )

    ET.SubElement(
        programme,
        "title"
    ).text = title

    ET.SubElement(
        programme,
        "desc"
    ).text = description


def parse_kickoff(timestamp):

    return datetime.strptime(
        timestamp,
        "%Y%m%d%H%M%S +0000",
    ).replace(
        tzinfo=timezone.utc
    )


def format_kickoff(timestamp):

    utc_time = parse_kickoff(timestamp)

    local_time = utc_time.astimezone(
        UK_TZ
    )

    return local_time.strftime(
        "%A %d %B %Y at %H:%M"
    )


def xml_time(dt):

    return dt.strftime(
        "%Y%m%d%H%M%S"
    ) + " +0000"


def get_next_match(fixtures, after_time):

    for match in fixtures:

        kickoff = parse_kickoff(
            match["kickoff"]
        )

        if kickoff > after_time:

            return match

    return None


def create_xmltv(fixtures, filename):

    tv = ET.Element(
        "tv",
        {
            "generator-info-name":
                "Rangers TV EPG"
        }
    )

    channel = ET.SubElement(
        tv,
        "channel",
        {
            "id": CHANNEL_ID
        }
    )

    ET.SubElement(
        channel,
        "display-name"
    ).text = "Rangers TV"


    # --------------------------------------------------
    # Create hourly "Next Game" entries
    # --------------------------------------------------

    now = datetime.now(timezone.utc)

    aligned_start = now.replace(
        minute=0,
        second=0,
        microsecond=0
    )


    for i in range(240):

        start = aligned_start + timedelta(
            hours=i
        )

        stop = start + timedelta(
            hours=1
        )


        # Check whether this hour overlaps a live match.
        live_match = None

        for match in fixtures:

            kickoff = parse_kickoff(
                match["kickoff"]
            )

            match_end = kickoff + timedelta(
                hours=2
            )

            if (
                start < match_end
                and stop > kickoff
            ):

                live_match = match
                break


        # Don't create a Next Game programme over a live match.
        if live_match is not None:
            continue


        # Find the next fixture after this hour.
        next_match = get_next_match(
            fixtures,
            start
        )


        if next_match is None:

            title = "Next Game"

            description = (
                "No upcoming Rangers fixture"
            )

        else:

            title = "Next Game"

            description = (
                f"{next_match['home']} vs "
                f"{next_match['away']}\n"
                f"Competition: "
                f"{next_match['competition']}\n"
                f"Venue: "
                f"{next_match['stadium']}\n"
                f"Kick-off: "
                f"{format_kickoff(next_match['kickoff'])}"
            )


        add_programme(
            tv,
            xml_time(start),
            xml_time(stop),
            title,
            description
        )


    # --------------------------------------------------
    # Create LIVE match entries
    # --------------------------------------------------

    for match in fixtures:

        kickoff = parse_kickoff(
            match["kickoff"]
        )

        match_end = kickoff + timedelta(
            hours=2
        )


        add_programme(
            tv,
            xml_time(kickoff),
            xml_time(match_end),
            (
                f"LIVE: "
                f"{match['home']} vs "
                f"{match['away']}"
            ),
            (
                f"{match['competition']}\n"
                f"Venue: {match['stadium']}\n"
                f"Kick-off: "
                f"{format_kickoff(match['kickoff'])}"
            )
        )


    # --------------------------------------------------
    # Write XMLTV file
    # --------------------------------------------------

    Path(filename).parent.mkdir(
        parents=True,
        exist_ok=True
    )


    ET.ElementTree(tv).write(
        filename,
        encoding="utf-8",
        xml_declaration=True
    )
