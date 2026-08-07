from pathlib import Path
from fixtures import get_fixtures
from teams import SPFL_TEAMS


Path("output").mkdir(exist_ok=True)


if __name__ == "__main__":

    for channel_id, team in SPFL_TEAMS.items():

        print("\n====================")
        print(team["name"])
        print("====================")

        fixtures = get_fixtures(
            team["urn"]
        )

        if not fixtures:
            print("No upcoming fixtures")
            continue

        for match in fixtures:
            print(
                f"{match['kickoff']} - "
                f"{match['home']} vs "
                f"{match['away']} - "
                f"{match['competition']}"
            )
