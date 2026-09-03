from app.lookup import AircraftLookup

db = AircraftLookup()

print()

print(db.lookup("004002"))
print(db.lookup("004013"))
print(db.lookup("801816"))
