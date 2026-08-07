from fixtures import get_fixtures
from xmltv import create_xmltv

if __name__ == "__main__":
    fixtures = get_fixtures()

    create_xmltv(
        fixtures,
        "output/rangerstv.xml"
    )

    print("Rangers TV EPG generated successfully")
