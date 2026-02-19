# f1-analysis — Project Summary

## Purpose

A fully-typed Python client library for the [OpenF1 API](https://openf1.org) with a multi-page Streamlit dashboard for visualizing Formula 1 performance data. The client provides ergonomic access to all 18 endpoints covering telemetry, timing, sessions, and standings data from 2023 onwards. No authentication required.

## Architecture

```
src/openf1/                          # Python client library
├── __init__.py                      # Public API (OpenF1Client, AsyncOpenF1Client, Filter)
├── client.py                        # Sync + async client classes (18 endpoint methods each)
├── _http.py                         # httpx transport (SyncTransport, AsyncTransport)
├── _filters.py                      # Query filter builder (equality, gt, gte, lt, lte)
├── exceptions.py                    # Exception hierarchy (connection, timeout, API, validation)
└── models/                          # 16 frozen Pydantic v2 models
    ├── car_data.py                  # Vehicle telemetry (~3.7 Hz)
    ├── championship.py              # Driver + team standings
    ├── driver.py                    # Driver info per session
    ├── interval.py                  # Gaps between drivers
    ├── lap.py                       # Sector times, speeds, segments
    ├── location.py                  # 3D car positions on track
    ├── meeting.py                   # Grand Prix weekends
    ├── overtake.py                  # Position changes
    ├── pit.py                       # Pit stop durations
    ├── position.py                  # Position timeline
    ├── race_control.py              # Flags, safety cars, incidents
    ├── session.py                   # Practice, qualifying, sprint, race
    ├── session_result.py            # Final standings (DNF/DNS/DSQ)
    ├── starting_grid.py             # Grid positions
    ├── stint.py                     # Tire compounds and ages
    ├── team_radio.py                # Audio recording URLs
    └── weather.py                   # Temperature, wind, humidity, rainfall

dashboard/                           # Streamlit multi-page dashboard
├── app.py                           # Main page — single-driver performance analysis
├── shared/                          # Shared utilities across pages
│   ├── __init__.py                  # Re-exports all shared symbols
│   ├── constants.py                 # F1_RED, COMPOUND_COLORS, PLOTLY_LAYOUT_DEFAULTS, etc.
│   ├── formatters.py                # format_lap_time(), format_delta()
│   ├── data_helpers.py              # Stint summarisation, compound lookup
│   ├── fetchers.py                  # @st.cache_data API fetchers + rate limiter
│   └── sidebar.py                   # render_session_sidebar() — shared session cascade
└── pages/
    └── 2_Driver_Comparison.py       # Compare up to 4 drivers side-by-side
```

## Dashboard

### Pages

**Driver Performance** (`app.py`) — Single-driver deep-dive:
- KPI metrics (total laps, best lap, avg lap, pit stops)
- Lap time progression chart (compound-colored in practice mode)
- Sector breakdown (stacked bar per lap)
- Speed trap comparison (driver avg/max vs session best)
- Stint summary table and chart (practice sessions)
- Tire strategy timeline (race/qualifying)
- Pit stop table

**Driver Comparison** (`pages/2_Driver_Comparison.py`) — Multi-driver comparison (2-4):
- Driver header with headshots and team color accent bars
- Best lap time metrics with delta to session best
- Stint comparison table (top 3 consistent stints, std dev < 2s) with sector averages
- Speed trap grouped bar chart (max I1/I2/ST per driver)
- Sector time stacked bar (S1/S2/S3 from each driver's fastest lap)

### Shared Module

The `dashboard/shared/` package extracts common functionality:
- **Fetchers**: 7 cached API functions with 350ms rate limiting for OpenF1's 3 req/s limit
- **Sidebar**: Reusable year → meeting → session → drivers cascade
- **Data helpers**: `summarise_stints()` and `summarise_stints_with_sectors()` with edge-lap outlier trimming
- **Color handling**: Teammate disambiguation via `COMPARISON_COLORS` fallback palette

## Data Flow

```
User code / Dashboard
  → OpenF1Client / AsyncOpenF1Client  (client.py)
    → build_query_params()             (_filters.py — Filter objects to query tuples)
    → SyncTransport / AsyncTransport   (_http.py — httpx GET with error mapping)
      → OpenF1 REST API                (https://api.openf1.org/v1)
    → Pydantic TypeAdapter.validate    (models/ — JSON → frozen model instances)
  ← list[Model]

Dashboard fetchers (@st.cache_data, TTL=600s)
  → _rate_limit() — 350ms spacing
  → OpenF1Client context manager
  → model_dump() to plain dicts for Streamlit serialization
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| HTTP client | httpx | Built-in sync + async, connection pooling |
| Data models | Pydantic v2 (frozen) | Validation, immutability, JSON parsing |
| Filter API | `Filter(gte=X, lte=Y)` dataclass | Ergonomic comparison operators alongside simple `key=value` equality |
| Project layout | `src/` layout | Prevents accidental imports from project root |
| Error handling | Custom exception hierarchy | Maps httpx errors to domain-specific exceptions |
| Dashboard framework | Streamlit | Rapid prototyping, built-in caching, multi-page support |
| Charts | Plotly | Interactive, dark-theme compatible, rich hover tooltips |
| Dashboard shared module | `dashboard/shared/` package | DRY across pages, shared caching and rate limiting |

## Dependencies

### Runtime (client)
- `httpx >= 0.27` — HTTP client
- `pydantic >= 2.0` — Data validation and models

### Dashboard
- `streamlit >= 1.38` — Web UI framework
- `plotly >= 5.22` — Interactive charts

### Development
- `pytest >= 8.0` + `respx >= 0.21` — Testing with httpx mocking
- `pytest-asyncio >= 0.23` — Async test support
- `pytest-cov >= 5.0` — Coverage reporting
- `ruff >= 0.4` — Linting
- `mypy >= 1.10` — Type checking

## Testing

- **61 tests** across 4 test files (client library)
- **94% code coverage**
- Test categories: filters (unit), HTTP transport (mocked), models (deserialization), client (integration with mocked API)
- Async tests via `pytest-asyncio` with `asyncio_mode = auto`

## API Endpoints (18 total)

`car_data`, `championship_drivers`, `championship_teams`, `drivers`, `intervals`, `laps`, `location`, `meetings`, `overtakes`, `pit`, `position`, `race_control`, `sessions`, `session_result`, `starting_grid`, `stints`, `team_radio`, `weather`

## Quick Start

### Client Library

```python
from openf1 import OpenF1Client, Filter

with OpenF1Client() as f1:
    meetings = f1.meetings(year=2024)
    laps = f1.laps(session_key=9161, driver_number=1, lap_number=Filter(gte=1, lte=10))
```

### Dashboard

```bash
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```
