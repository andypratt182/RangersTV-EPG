import requests
from datetime import datetime, timezone, timedelta


BBC_FIXTURES_URL = (
    "https://web-cdn.api.bbci.co.uk/"
    "wc-poll-data/container/sport-data-scores-fixtures"
)


def get_fixtures():

    today = datetime.now(timezone.utc).date()

    start_date = today.isoformat()

    end_date = (
        today + timedelta(days=60)
    ).isoformat()


    params = {

        "selectedStartDate": start_date,

        "selectedEndDate": end_date,

        "todayDate": start_date,

        "urn":
            "urn:bbc:sportsdata:"
            "football:team:rangers"

    }


    headers = {

        "User-Agent":
            "RangersTV-EPG/1.0",

        "Accept":
            "application/json"

    }


    response = requests.get(

        BBC_FIXTURES_URL,

        params=params,

        headers=headers,

        timeout=20

    )


    response.raise_for_status()


    data = response.json()


    fixtures = []


    for event_group in data.get(
        "eventGroups",
        []
    ):

        for secondary_group in event_group.get(
            "secondaryGroups",
            []
        ):

            competition = (
                secondary_group.get(
                    "displayLabel",
                    "Football"
                )
            )


            for event in secondary_group.get(
                "events",
                []
            ):

                kickoff = datetime.fromisoformat(

                    event["startDateTime"]
                    .replace(
                        "Z",
                        "+00:00"
                    )

                )


                # Ignore old fixtures
                if kickoff < datetime.now(timezone.utc):
                    continue


                home = event["home"]["fullName"]

                away = event["away"]["fullName"]


                fixtures.append({

                    "home": home,

                    "away": away,

                    "competition":
                        competition,

                    "stadium":
                        (
                            "Ibrox Stadium"
                            if home == "Rangers"
                            else "Away"
                        ),

                    "kickoff":
                        kickoff.strftime(
                            "%Y%m%d%H%M%S +0000"
                        ),

                    "tv":
                        ""

                })


    fixtures.sort(
        key=lambda x: x["kickoff"]
    )


    return fixtures
