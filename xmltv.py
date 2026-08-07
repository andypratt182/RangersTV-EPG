from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET


CHANNEL_ID = "rangerstv"

UK_TZ = ZoneInfo("Europe/London")


def add_programme(tv, start, stop, title, description):

    programme = ET.SubElement(
        tv,
        "programme",
        {
            "start": start,
            "stop": stop,
            "channel": CHANNEL_ID
        }
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
        "%Y%m%d%H%M%S +0000"
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



    if fixtures:

        next_match = fixtures[0]

        next_game = (
            f"{next_match['home']} vs "
            f"{next_match['away']}\n"
            f"Competition: "
            f"{next_match['competition']}\n"
            f"Venue: "
            f"{next_match['stadium']}\n"
            f"Kick-off: "
            f"{format_kickoff(next_match['kickoff'])}"
        )

    else:

        next_game = (
            "No upcoming Rangers fixture"
        )



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


        match_on = False


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
                match_on = True
                break



        if not match_on:

            add_programme(
                tv,
                xml_time(start),
                xml_time(stop),
                "Next Game",
                next_game
            )



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



    Path(filename).parent.mkdir(
        parents=True,
        exist_ok=True
    )


    ET.ElementTree(tv).write(
        filename,
        encoding="utf-8",
        xml_declaration=True
    )
