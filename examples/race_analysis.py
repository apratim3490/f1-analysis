"""Multi-endpoint race analysis example."""

from openf1 import Filter, OpenF1Client


def analyze_race(year: int, meeting_name_contains: str) -> None:
    """Analyze a specific race by year and partial meeting name."""
    with OpenF1Client() as f1:
        # 1. Find the meeting
        meetings = f1.meetings(year=year)
        match = [m for m in meetings if meeting_name_contains.lower() in (m.meeting_name or "").lower()]
        if not match:
            print(f"No meeting found matching '{meeting_name_contains}' in {year}")
            return
        meeting = match[0]
        print(f"Race: {meeting.meeting_official_name}")
        print(f"Circuit: {meeting.circuit_short_name}, {meeting.country_name}")
        print()

        # 2. Find the race session
        sessions = f1.sessions(meeting_key=meeting.meeting_key, session_type="Race")
        if not sessions:
            print("No race session found.")
            return
        session_key = sessions[0].session_key

        # 3. Get race results
        results = f1.session_result(session_key=session_key)
        print("=== Race Results ===")
        for r in sorted(results, key=lambda x: x.position or 99):
            gap = f"+{r.gap_to_leader}" if r.position and r.position > 1 else "WINNER"
            status = f" ({r.status})" if r.status and r.status != "Finished" else ""
            print(f"  P{r.position}: {r.full_name} [{r.team_name}] {gap}{status}")

        # 4. Pit stop analysis
        pits = f1.pit(session_key=session_key)
        print(f"\n=== Pit Stops ({len(pits)} total) ===")
        if pits:
            driver_pits: dict[int, list[float]] = {}
            for p in pits:
                if p.driver_number and p.pit_duration:
                    driver_pits.setdefault(p.driver_number, []).append(p.pit_duration)

            drivers = {d.driver_number: d for d in f1.drivers(session_key=session_key)}
            for num, durations in sorted(driver_pits.items()):
                name = drivers.get(num)
                label = name.name_acronym if name else str(num)
                stops = ", ".join(f"{d:.1f}s" for d in durations)
                print(f"  {label}: {len(durations)} stop(s) - [{stops}]")

        # 5. Stint/tire strategy
        stints = f1.stints(session_key=session_key)
        print(f"\n=== Tire Strategy (top 3) ===")
        top_drivers = [r.driver_number for r in sorted(results, key=lambda x: x.position or 99)[:3]]
        for num in top_drivers:
            driver_stints = sorted(
                [s for s in stints if s.driver_number == num],
                key=lambda s: s.stint_number or 0,
            )
            drivers_map = {d.driver_number: d for d in f1.drivers(session_key=session_key)}
            name = drivers_map.get(num)
            label = name.name_acronym if name else str(num)
            compounds = " → ".join(s.compound or "?" for s in driver_stints)
            print(f"  {label}: {compounds}")

        # 6. Weather summary
        weather = f1.weather(session_key=session_key)
        if weather:
            temps = [w.air_temperature for w in weather if w.air_temperature is not None]
            if temps:
                print(f"\n=== Weather ===")
                print(f"  Air temp: {min(temps):.1f}°C - {max(temps):.1f}°C")
                rain = any(w.rainfall and w.rainfall > 0 for w in weather)
                print(f"  Rain: {'Yes' if rain else 'No'}")


if __name__ == "__main__":
    analyze_race(2024, "Bahrain")
