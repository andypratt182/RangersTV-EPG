next_game = "No upcoming fixture"

if fixtures:
    match = fixtures[0]

    next_game = (
        f"{match['home']} vs {match['away']}\n"
        f"{match['competition']}\n"
        f"Venue: {match['stadium']}\n"
        f"Kick-off: {match['kickoff']}"
    )
