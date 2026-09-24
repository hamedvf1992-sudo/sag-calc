from sag_tension import analyze

r = analyze({"weather_zone": "Heavy"})
assert r["results"]
assert r["display_case"]["sag"] > 0
assert len(r["curve"]["x"]) == len(r["curve"]["y"])
print("OK")
print("Governing:", r["governing_state"])
print("Display case:", r["display_case"]["name"], "sag=", round(r["display_case"]["sag"], 3))
