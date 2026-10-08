"""Generate a clearly synthetic, recent Fitbit-shaped ZIP. Never real records."""
import argparse
from datetime import date, timedelta
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def create(path: Path, end: date):
    days = [end - timedelta(days=30 - i) for i in range(31)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("SYNTHETIC_ONLY.txt", "Generated test data. Not a person or a vendor account export.")
        rhr = "timestamp,beats per minute,data source\n"
        hrv = "timestamp,average heart rate variability milliseconds,data source\n"
        for i, day in enumerate(days):
            changed = i >= 28
            rhr += f"{day}T04:00:00Z,{68 if changed else 60 + i % 3},Synthetic Fitbit\n"
            hrv += f"{day}T04:00:00Z,{28 if changed else 45 + i % 4},Synthetic Fitbit\n"
            sleep = [{"logId": i, "startTime": f"{day}T00:00:00", "endTime": f"{day}T08:00:00",
                      "minutesAsleep": 340 if changed else 440 + i % 3, "mainSleep": True}]
            archive.writestr(f"Takeout/Google Health/sleep-{day}.json", json.dumps(sleep))
            archive.writestr(f"Takeout/Google Health/steps-{day}.json", json.dumps([
                {"dateTime": f"{day.strftime('%m/%d/%y')} 12:00:00", "value": "300"},
                {"dateTime": f"{day.strftime('%m/%d/%y')} 18:00:00", "value": "400"}]))
        archive.writestr("Takeout/Google Health/daily_resting_heart_rate.csv", rhr)
        archive.writestr("Takeout/Google Health/daily_heart_rate_variability.csv", hrv)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/private/synthetic-fitbit.zip"))
    parser.add_argument("--end-date", type=date.fromisoformat, default=date.today() - timedelta(days=1))
    args = parser.parse_args()
    print(f"Synthetic example created: {create(args.output, args.end_date)}")
