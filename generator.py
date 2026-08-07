from pathlib import Path

from fixtures import get_fixtures
from teams import SPFL_TEAMS


# Ensure GitHub Pages always has something to upload
output_folder = Path("output")
output_folder.mkdir(
    exist_ok=True
)


if __name__ == "__main__":

    report_lines = []

    for channel_id, team in SPFL_TEAMS.items():

        print("\n====================")
        print(team["name"])
        print("====================")

        report_lines.append(
            f"\n{team['name']}\n"
        )

        try:

            fixtures = get_fixtures(
                team["urn"]
            )

            if not fixtures:

                print(
                    "No upcoming fixtures"
                )

                report_lines.append(
                    "No upcoming fixtures\n"
                )

                continue


            for match in fixtures:

                line = (
                    f"{match['kickoff']} - "
                    f"{match['home']} vs "
                    f"{match['away']} - "
                    f"{match['competition']}"
                )

                print(line)

                report_lines.append(
                    line + "\n"
                )


        except Exception as e:

            error = (
                f"ERROR loading "
                f"{team['name']}: {e}"
            )

            print(error)

            report_lines.append(
                error + "\n"
            )


    # Create a temporary file so the
    # GitHub Pages upload step succeeds.
    (output_folder / "test.txt").write_text(
        "".join(report_lines),
        encoding="utf-8"
    )


    print("\nSPFL fixture test completed")
