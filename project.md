# f1-analysis — Project Summary

## Purpose

A fully-typed Python client library for the [OpenF1 API](https://openf1.org) with a multi-page Streamlit dashboard for visualizing Formula 1 performance data. The client provides ergonomic access to all 18 endpoints covering telemetry, timing, sessions, and standings data from 2023 onwards. No authentication required. The dashboard supports both OpenF1 and FastF1 as data backends.

## Architecture

### 3-Tier Dashboard Architecture

```
UI Layer (app.py, pages/2_Driver_Comparison.py)
  → only Streamlit widgets + Plotly charts
  → catches F1DataError (generic)

Service Layer (shared/services/)
  → all business logic, KPI computation, aggregations
  → returns frozen dataclasses

Data Layer (shared/data/)
  → source-agnostic repository interface
  → OpenF1 + FastF1 implementations
  → all calls logged to dashboard/logs/api_calls.log
```

### File Structure

```
src/openf1/                          # Python client library
├── __init__.py                      # Public API (OpenF1Client, AsyncOpenF1Client, Filter)
├── client.py                        # Sync + async client classes (18 endpoint methods each)
├── _http.py                         # httpx transport (SyncTransport, AsyncTransport)
├── _filters.py                      # Query filter builder (equality, gt, gte, lt, lte)
├── exceptions.py                    # Exception hierarchy (connection, timeout, API, validation)
└── models/                          # 16 frozen Pydantic v2 models

dashboard/                           # Streamlit multi-page dashboard
├── app.py                           # Main page — single-driver performance analysis (UI only)
├── logs/                            # API call log output (.gitignore'd)
├── shared/                          # Shared utilities across pages
│   ├── __init__.py                  # Re-exports all shared symbols (grouped by concern)
│   ├── constants.py                 # F1_RED, COMPOUND_COLORS, PLOTLY_LAYOUT_DEFAULTS, etc.
│   ├── formatters.py                # format_lap_time(), format_delta()
│   ├── api_logging.py               # File logger + @log_api_call / @log_service_call decorators
│   ├── sidebar.py                   # render_session_sidebar() — shared session cascade
│   ├── data/                        # Data Layer — source-agnostic repositories
│   │   ├── __init__.py              # get_repository() factory, re-exports
│   │   ├── errors.py                # F1DataError (source-agnostic exception)
│   │   ├── types.py                 # TypedDict contracts for all data shapes
│   │   ├── base.py                  # ABC: F1DataRepository (7 abstract methods)
│   │   ├── source.py                # DataSource enum, get_active_source(), fastf1_available()
│   │   ├── openf1_repo.py           # OpenF1 API implementation (with @st.cache_data)
│   │   └── fastf1_repo.py           # FastF1 implementation (with @st.cache_resource)
│   └── services/                    # Service Layer — business logic
│       ├── __init__.py              # Re-exports
│       ├── common.py                # Shared pure functions (lap filtering, color assignment)
│       ├── stint_helpers.py          # Stint summarisation, compound lookup
│       ├── driver_performance.py    # Single-driver: KPIs, lap progression, sectors, speed traps
│       └── driver_comparison.py     # Multi-driver: best laps, stint comparison, speed traps
└── pages/
    └── 2_Driver_Comparison.py       # Compare up to 4 drivers side-by-side (UI only)
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
- Best lap time metrics with delta to session best, tyre compound + age, and track temperature
- Stint comparison table (top 3 consistent stints, std dev < 2s) with sector averages
- Speed trap grouped bar chart (max I1/I2/ST per driver)
- Sector time stacked bar (S1/S2/S3 from each driver's fastest lap)
- Track map animation (best lap overlay with Play/Pause, real-time playback, equal aspect ratio)
- Speed vs Time line chart (best lap telemetry per driver)
- RPM vs Time line chart (best lap telemetry per driver)

### Data Layer

The `shared/data/` package provides a source-agnostic repository interface:
- **F1DataRepository** (ABC): 9 abstract methods (get_meetings, get_sessions, get_drivers, get_laps, get_all_laps, get_stints, get_pits, get_car_telemetry, get_location)
- **OpenF1Repository**: Uses OpenF1Client with 350ms rate limiting and @st.cache_data
- **FastF1Repository**: Uses fastf1 library with @st.cache_resource for session loading, includes telemetry via `lap.get_telemetry()`
- **F1DataError**: Generic exception caught by all UI layers (replaces OpenF1Error)
- **DataSource** (`data/source.py`): Enum for backend selection (OpenF1/FastF1) with session state integration
- **TypedDict contracts**: DriverInfo, LapData, StintData, PitData, MeetingData, SessionData, CarTelemetry, LocationPoint
- **API call logging**: All data and service calls logged to `dashboard/logs/api_calls.log` via `shared/api_logging.py`

### Service Layer

The `shared/services/` package encapsulates all business logic:
- **DriverPerformanceService**: KPIs, lap progression, sector breakdown, speed traps, stint summaries
- **DriverComparisonService**: Best laps, stint comparison with insights, speed trap comparison, sector comparison, telemetry traces (speed/RPM), track map animation
- **common.py**: Pure functions for lap filtering, color assignment, speed stats, ideal lap computation
- All service methods return frozen dataclasses for immutability

### Shared Module

- **Sidebar**: Reusable year → meeting → session → drivers cascade (uses repository)
- **Stint helpers** (`services/stint_helpers.py`): `summarise_stints()`, `summarise_stints_with_sectors()` with edge-lap outlier trimming, `get_compound_for_lap()`, `get_tyre_age_for_lap()`
- **API logging** (`api_logging.py`): Cross-cutting file logger with `@log_api_call` and `@log_service_call` decorators
- **Color handling**: Teammate disambiguation via `COMPARISON_COLORS` fallback palette

## Data Flow

```
User code / Dashboard
  → Service Layer (business logic, KPIs, aggregations)
    → Data Layer (F1DataRepository interface)
      → OpenF1Repository / FastF1Repository
        → OpenF1 REST API / FastF1 library
      → @log_api_call → dashboard/logs/api_calls.log
    → @log_service_call → dashboard/logs/api_calls.log
  ← Frozen dataclasses / TypedDict data
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | 3-tier (UI → Service → Data) | Separation of concerns, testable business logic |
| Data access | Repository pattern (ABC) | Source-agnostic, swappable backends |
| Error handling | F1DataError (generic) | UI doesn't depend on specific backend exceptions |
| Data contracts | TypedDict | Lightweight, IDE-friendly, no runtime overhead |
| Service returns | Frozen dataclasses | Immutable, typed, structured results |
| API logging | File-based (@log_api_call) | Observability without external dependencies |
| HTTP client | httpx | Built-in sync + async, connection pooling |
| Data models | Pydantic v2 (frozen) | Validation, immutability, JSON parsing |
| Dashboard framework | Streamlit | Rapid prototyping, built-in caching, multi-page support |
| Charts | Plotly | Interactive, dark-theme compatible, rich hover tooltips |

## Dependencies

### Runtime (client)
- `httpx >= 0.27` — HTTP client
- `pydantic >= 2.0` — Data validation and models

### Dashboard
- `streamlit >= 1.38` — Web UI framework
- `plotly >= 5.22` — Interactive charts
- `fastf1` (optional) — Alternative data backend

### Development
- `pytest >= 8.0` + `respx >= 0.21` — Testing with httpx mocking
- `pytest-asyncio >= 0.23` — Async test support
- `pytest-cov >= 5.0` — Coverage reporting
- `ruff >= 0.4` — Linting
- `mypy >= 1.10` — Type checking

## Testing

- **224 tests** across client library (`tests/openf1/`) and dashboard (`tests/dashboard/`)
- Test categories: filters (unit), HTTP transport (mocked), models (deserialization), client (integration with mocked API), dashboard services, data layer, stint helpers, logging
- Async tests via `pytest-asyncio` with `asyncio_mode = auto`

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
