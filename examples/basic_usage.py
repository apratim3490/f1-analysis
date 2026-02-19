"""Basic usage examples for the OpenF1 client."""

from openf1 import Filter, OpenF1Client


def main() -> None:
    with OpenF1Client() as f1:
        # Get all 2024 meetings (Grand Prix weekends)
        print("=== 2024 Meetings ===")
        meetings = f1.meetings(year=2024)
        for m in meetings[:5]:
            print(f"  {m.meeting_name} - {m.location}, {m.country_name}")

        if not meetings:
            print("  No meetings found.")
            return

        # Get sessions for the first meeting
        meeting_key = meetings[0].meeting_key
        print(f"\n=== Sessions for {meetings[0].meeting_name} ===")
        sessions = f1.sessions(meeting_key=meeting_key)
        for s in sessions:
            print(f"  {s.session_name} ({s.session_type})")

        # Find a race session
        race_sessions = [s for s in sessions if s.session_type == "Race"]
        if not race_sessions:
            print("  No race session found.")
            return

        session_key = race_sessions[0].session_key
        print(f"\n=== Drivers in Race (session_key={session_key}) ===")
        drivers = f1.drivers(session_key=session_key)
        for d in sorted(drivers, key=lambda x: x.driver_number or 0):
            print(f"  #{d.driver_number} {d.full_name} - {d.team_name}")

        # Get laps 1-5 for driver #1
        print(f"\n=== Laps 1-5 for driver #1 ===")
        laps = f1.laps(
            session_key=session_key,
            driver_number=1,
            lap_number=Filter(gte=1, lte=5),
        )
        for lap in laps:
            duration = f"{lap.lap_duration:.3f}s" if lap.lap_duration else "N/A"
            print(f"  Lap {lap.lap_number}: {duration}")

        # Get weather during the session
        print(f"\n=== Weather ===")
        weather = f1.weather(session_key=session_key)
        if weather:
            w = weather[0]
            print(f"  Air: {w.air_temperature}°C, Track: {w.track_temperature}°C")
            print(f"  Humidity: {w.humidity}%, Wind: {w.wind_speed} m/s")


if __name__ == "__main__":
    main()
