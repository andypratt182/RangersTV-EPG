from pathlib import Path
from datetime import datetime, timedelta
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

    ET.SubElement(programme, "title").text = title
    ET.SubElement(programme, "desc").text = description



def create_xmltv(fixtures, filename):

    tv = ET.Element(
        "tv",
        {
            "generator-info-name": "Rangers TV EPG"
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


    next_game = "No upcoming fixture"

    if fixtures:

        match = fixtures[0]

        next_game = (
            f"{match['home']} vs {match['away']}\n"
            f"{match['competition']}\n"
            f"Venue: {match['stadium']}\n"
            f"Kick-off: {match['kickoff']}"
        )


    now = datetime.now()


    # Generate rolling Next Game entries
    for i in range(180):

        start = now + timedelta(
            hours=i * 2
        )

        stop = start + timedelta(
            hours=2
        )


        add_programme(
            tv,
            start.strftime("%Y%m%d%H%M%S") + " +0100",
            stop.strftime("%Y%m%d%H%M%S") + " +0100",
            "Next Game",
            next_game
        )


    # Add live matches
    for match in fixtures:

        add_programme(
            tv,
            match["kickoff"],
            match["kickoff"],
            f"LIVE: {match['home']} vs {match['away']}",
            (
                f"{match['competition']}\n"
                f"Venue: {match['stadium']}\n"
                f"TV: {match['tv']}"
            )
        )


    Path(filename).parent.mkdir(
        exist_ok=True
    )

    ET.ElementTree(tv).write(
        filename,
        encoding="utf-8",
        xml_declaration=True
    )
