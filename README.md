# f1-analysis

Fully-typed Python client for the [OpenF1 API](https://openf1.org), providing access to Formula 1 telemetry, timing, sessions, and standings data (2023+).

## Installation

```bash
# Clone and set up
cd C:\Developer\f1-analysis
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
```

## Quick Start

```python
from openf1 import OpenF1Client, Filter

with OpenF1Client() as f1:
    # Get all 2024 meetings
    meetings = f1.meetings(year=2024)

    # Get drivers for a session
    drivers = f1.drivers(session_key=9161)

    # Filter laps with comparison operators
    laps = f1.laps(
        session_key=9161,
        driver_number=1,
        lap_number=Filter(gte=5, lte=10),
    )

    # Get weather data
    weather = f1.weather(meeting_key=1219)
```

### Async Usage

```python
import asyncio
from openf1 import AsyncOpenF1Client

async def main():
    async with AsyncOpenF1Client() as f1:
        drivers = await f1.drivers(session_key=9161)
        print(drivers)

asyncio.run(main())
```

## Endpoints

All 18 OpenF1 API endpoints are supported:

| Method | Description |
|--------|-------------|
| `car_data()` | Vehicle telemetry (speed, throttle, brake, RPM, gear, DRS) |
| `championship_drivers()` | Driver championship standings |
| `championship_teams()` | Team championship standings |
| `drivers()` | Driver information per session |
| `intervals()` | Real-time gaps between drivers |
| `laps()` | Lap data with sector times and speeds |
| `location()` | Car positions on track (3D coordinates) |
| `meetings()` | Grand Prix weekends and test events |
| `overtakes()` | Position change events |
| `pit()` | Pit stop information |
| `position()` | Driver position changes |
| `race_control()` | Flags, safety cars, incidents |
| `sessions()` | Practice, qualifying, sprint, race |
| `session_result()` | Final standings after a session |
| `starting_grid()` | Race starting grid positions |
| `stints()` | Tire stint information |
| `team_radio()` | Driver-team radio communications |
| `weather()` | Track weather conditions |

## Filtering

Simple equality filters use keyword arguments. For comparison operators, use `Filter`:

```python
from openf1 import Filter

# Equality
f1.drivers(session_key=9161, driver_number=1)

# Greater than or equal
f1.laps(session_key=9161, lap_number=Filter(gte=5))

# Range
f1.laps(session_key=9161, lap_number=Filter(gte=5, lte=10))

# Date filtering
f1.car_data(session_key=9161, date=Filter(gte="2023-03-05T15:00:00"))
```

## Running Tests

```bash
pytest tests/ -v
pytest tests/ --cov=openf1 --cov-report=term-missing
```

## Examples

```bash
python examples/basic_usage.py
python examples/race_analysis.py
```
