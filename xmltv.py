from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

from teams import SPFL_TEAMS


UK_TZ = ZoneInfo("Europe/London")

MATCH_DURATION = timedelta(hours=2)


def add_programme(
    tv,
    channel_id,
    start,
    stop,
    title,
    description
):

    if stop <= start:
        return

    programme = ET.SubElement(
        tv,
        "programme",
        {
            "start": start,
            "stop": stop,
            "channel": channel_id,
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

    return utc_time.astimezone(
        UK_TZ
    ).strftime(
        "%A %d %B %Y at %H:%M"
    )


def xml_time(dt):

    return dt.strftime(
        "%Y%m%d%H%M%S"
    ) + " +0000"


def get_next_match(fixtures, channel_id, after_time):

    for match in fixtures:

        if match.get("channel_id") != channel_id:
            continue

        kickoff = parse_kickoff(
            match["kickoff"]
        )

        if kickoff > after_time:
            return match

    return None


def create_next_game_programme(
    tv,
    channel_id,
    start,
    stop,
    fixtures
):

    next_match = get_next_match(
        fixtures,
        channel_id,
        start
    )


    if next_match:

        description = (
            f"{next_match['home']} vs "
            f"{next_match['away']}\n"
            f"Competition: "
            f"{next_match['competition']}\n"
            f"Venue: "
            f"{next_match.get('stadium','Venue TBC')}\n"
            f"Kick-off: "
            f"{format_kickoff(next_match['kickoff'])}"
        )

    else:

        description = (
            "No upcoming fixture"
        )


    add_programme(
        tv,
        channel_id,
        xml_time(start),
        xml_time(stop),
        "Next Game",
        description
    )


def create_channel_entries(tv):

    for channel_id, team in SPFL_TEAMS.items():

        channel = ET.SubElement(
            tv,
            "channel",
            {
                "id": channel_id
            }
        )

        ET.SubElement(
            channel,
            "display-name"
        ).text = team["name"]


def create_xmltv(fixtures, filename):

    tv = ET.Element(
        "tv",
        {
            "generator-info-name":
                "SPFL IPTV EPG"
        }
    )


    create_channel_entries(tv)


    fixtures = sorted(
        fixtures,
        key=lambda x: x["kickoff"]
    )


    now = datetime.now(
        timezone.utc
    )

    epg_start = now.replace(
        minute=0,
        second=0,
        microsecond=0
    )

    epg_end = epg_start + timedelta(
        hours=240
    )


    # Create timeline separately for each club

    for channel_id in SPFL_TEAMS:

        channel_matches = [
            f for f in fixtures
            if f.get("channel_id") == channel_id
        ]


        current = epg_start


        for match in channel_matches:

            kickoff = parse_kickoff(
                match["kickoff"]
            )

            match_end = kickoff + MATCH_DURATION


            if match_end <= epg_start:
                continue


            if kickoff >= epg_end:
                break


            if current < kickoff:

                create_next_game_programme(
                    tv,
                    channel_id,
                    current,
                    kickoff,
                    fixtures
                )


            live_start = max(
                kickoff,
                epg_start
            )

            live_end = min(
                match_end,
                epg_end
            )


            add_programme(
                tv,
                channel_id,
                xml_time(live_start),
                xml_time(live_end),
                (
                    f"LIVE: "
                    f"{match['home']} vs "
                    f"{match['away']}"
                ),
                (
                    f"{match['competition']}\n"
                    f"Venue: "
                    f"{match.get('stadium','Venue TBC')}\n"
                    f"Kick-off: "
                    f"{format_kickoff(match['kickoff'])}"
                )
            )


            current = max(
                current,
                match_end
            )


        if current < epg_end:

            create_next_game_programme(
                tv,
                channel_id,
                current,
                epg_end,
                fixtures
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
