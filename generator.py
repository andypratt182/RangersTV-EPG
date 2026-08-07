from fixtures import get_fixtures
from xmltv import create_xmltv


RANGERS_URN = (
    "urn:bbc:sportsdata:football:team:rangers"
)


if __name__ == "__main__":

    fixtures = get_fixtures(
        RANGERS_URN
    )

    create_xmltv(
        fixtures,
        "output/rangerstv.xml"
    )

    print(
        "Rangers TV EPG generated successfully"
    )
