from app.alert_lookup import AlertLookup

lookup = AlertLookup()

print("Loaded:", len(lookup.aircraft))

print()

samples = [
    "000004",
    "001108",
    "AE1234"
]

for hexcode in samples:

    print("--------------------------------")

    print(hexcode)

    print(lookup.get(hexcode))
