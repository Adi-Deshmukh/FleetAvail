import json
import urllib.request

BASE = "http://127.0.0.1:8000"


def main():
    for path in ["/health", "/api/fleet/summary", "/api/fleet/aircraft"]:
        with urllib.request.urlopen(BASE + path, timeout=5) as response:
            print(path, "OK", response.status)

    request = urllib.request.Request(
        BASE + "/api/predict",
        data=json.dumps(
            {
                "aircraft_id": "AF-003",
                "component": "ENGINE",
                "telemetry": {
                    "egt_c": 790,
                    "vibration_g": 0.9,
                    "oil_pressure_kpa": 290,
                },
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        print("/api/predict", "OK", response.status, response.read().decode()[:300])


if __name__ == "__main__":
    main()
