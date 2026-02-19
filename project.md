# f1-analysis — Project Summary

## Purpose

A fully-typed Python client library for the [OpenF1 API](https://openf1.org), providing ergonomic access to all 18 endpoints covering Formula 1 telemetry, timing, sessions, and standings data from 2023 onwards. No authentication required for historical data.

## Architecture

```
src/openf1/
├── __init__.py           # Public API surface (OpenF1Client, AsyncOpenF1Client, Filter)
├── client.py             # Sync + async client classes with 18 endpoint methods each
├── _http.py              # Low-level httpx transport (SyncTransport, AsyncTransport)
├── _filters.py           # Query filter builder (equality, gt, gte, lt, lte)
├── exceptions.py         # Exception hierarchy (connection, timeout, API, validation)
└── models/               # 16 frozen Pydantic v2 models (one per endpoint group)
    ├── car_data.py       # Vehicle telemetry (~3.7 Hz)
    ├── championship.py   # Driver + team standings
    ├── driver.py         # Driver info per session
    ├── interval.py       # Gaps between drivers
    ├── lap.py            # Sector times, speeds, segments
    ├── location.py       # 3D car positions on track
    ├── meeting.py        # Grand Prix weekends
    ├── overtake.py       # Position changes
    ├── pit.py            # Pit stop durations
    ├── position.py       # Position timeline
    ├── race_control.py   # Flags, safety cars, incidents
    ├── session.py        # Practice, qualifying, sprint, race
    ├── session_result.py # Final standings (DNF/DNS/DSQ)
    ├── starting_grid.py  # Grid positions
    ├── stint.py          # Tire compounds and ages
    ├── team_radio.py     # Audio recording URLs
    └── weather.py        # Temperature, wind, humidity, rainfall
```

## Data Flow

```
User code
  → OpenF1Client / AsyncOpenF1Client  (client.py)
    → build_query_params()             (_filters.py — converts Filter objects to query tuples)
    → SyncTransport / AsyncTransport   (_http.py — httpx GET with error mapping)
      → OpenF1 REST API                (https://api.openf1.org/v1)
    → Pydantic TypeAdapter.validate    (models/ — JSON → frozen model instances)
  ← list[Model]
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| HTTP client | httpx | Built-in sync + async, connection pooling |
| Data models | Pydantic v2 (frozen) | Validation, immutability, JSON parsing |
| Filter API | `Filter(gte=X, lte=Y)` dataclass | Ergonomic comparison operators alongside simple `key=value` equality |
| Project layout | `src/` layout | Prevents accidental imports from project root |
| Error handling | Custom exception hierarchy | Maps httpx errors to domain-specific exceptions |

## Dependencies

### Runtime
- `httpx >= 0.27` — HTTP client
- `pydantic >= 2.0` — Data validation and models

### Development
- `pytest >= 8.0` + `respx >= 0.21` — Testing with httpx mocking
- `pytest-asyncio >= 0.23` — Async test support
- `pytest-cov >= 5.0` — Coverage reporting
- `ruff >= 0.4` — Linting
- `mypy >= 1.10` — Type checking

## Testing

- **61 tests** across 4 test files
- **94% code coverage**
- Test categories: filters (unit), HTTP transport (mocked), models (deserialization), client (integration with mocked API)
- Async tests via `pytest-asyncio` with `asyncio_mode = auto`

## API Endpoints (18 total)

`car_data`, `championship_drivers`, `championship_teams`, `drivers`, `intervals`, `laps`, `location`, `meetings`, `overtakes`, `pit`, `position`, `race_control`, `sessions`, `session_result`, `starting_grid`, `stints`, `team_radio`, `weather`

## Quick Start

```python
from openf1 import OpenF1Client, Filter

with OpenF1Client() as f1:
    meetings = f1.meetings(year=2024)
    laps = f1.laps(session_key=9161, driver_number=1, lap_number=Filter(gte=1, lte=10))
```
