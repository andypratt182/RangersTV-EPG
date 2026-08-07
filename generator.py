from pathlib import Path

from fixtures import get_fixtures
from teams import SPFL_TEAMS
from xmltv import create_xmltv


output_folder = Path("output")
output_folder.mkdir(
    exist_ok=True
)


if __name__ == "__main__":

    all_fixtures = []


    for channel_id, team in SPFL_TEAMS.items():

        print("\n====================")
        print(team["name"])
        print("====================")


        try:

            fixtures = get_fixtures(
                team
            )


            if not fixtures:

                print(
                    "No upcoming fixtures"
                )

                continue


            for match in fixtures:

                # Add the IPTV channel ID
                # so XMLTV knows where to place it
                match["channel_id"] = channel_id


                print(
                    f"{match['kickoff']} - "
                    f"{match['home']} vs "
                    f"{match['away']} - "
                    f"{match['competition']}"
                )


                all_fixtures.append(
                    match
                )


        except Exception as e:

            print(
                f"ERROR loading "
                f"{team['name']}: {e}"
            )


    print("\n====================")
    print(
        f"Total fixtures found: {len(all_fixtures)}"
    )
    print("====================")


    create_xmltv(
        all_fixtures,
        "output/spfl.xml"
    )


    print(
        "SPFL EPG generated successfully"
    )
