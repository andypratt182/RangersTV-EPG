from pathlib import Path
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET


CHANNEL_ID = "rangerstv"


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



def create_xmltv(fixtures, filename):

    tv = ET.Element(
        "tv",
        {
            "generator-info-name": "Rangers TV EPG"
        }
    )


    # Channel information
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



    # Find next Rangers fixture
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
            f"{next_match['kickoff']}"
        )

    else:

        next_game = "No upcoming Rangers fixture"



    # Generate Next Game schedule
    now = datetime.now(timezone.utc)

    aligned_start = now.replace(
        minute=0,
        second=0,
        microsecond=0
    )


    for i in range(240):

        start = aligned_start + timedelta(hours=i)
        stop = start + timedelta(hours=1)

        overlap = False


        # Avoid Next Game during live matches
        for match in fixtures:

            kickoff = datetime.strptime(
                match["kickoff"].replace(" +0000", ""),
                "%Y%m%d%H%M%S"
            ).replace(
                tzinfo=timezone.utc
            )


            match_end = kickoff + timedelta(hours=2)


            if start < match_end and stop > kickoff:
                overlap = True
                break


        if not overlap:

            add_programme(
                tv,
                start.strftime(
                    "%Y%m%d%H%M%S"
                ) + " +0000",

                stop.strftime(
                    "%Y%m%d%H%M%S"
                ) + " +0000",

                "Next Game",

                next_game
            )



    # Generate LIVE match entries
    for match in fixtures:

        kickoff = datetime.strptime(
            match["kickoff"].replace(" +0000", ""),
            "%Y%m%d%H%M%S"
        ).replace(
            tzinfo=timezone.utc
        )


        match_end = kickoff + timedelta(hours=2)


        add_programme(
            tv,

            kickoff.strftime(
                "%Y%m%d%H%M%S"
            ) + " +0000",

            match_end.strftime(
                "%Y%m%d%H%M%S"
            ) + " +0000",

            f"LIVE: {match['home']} vs {match['away']}",

            (
                f"{match['competition']}\n"
                f"Venue: {match['stadium']}\n"
                f"Kick-off: {match['kickoff']}"
            )
        )



    # Save XML
    Path(filename).parent.mkdir(
        exist_ok=True
    )


    ET.ElementTree(tv).write(
        filename,
        encoding="utf-8",
        xml_declaration=True
    )
