"""Tests for the filter builder."""

from __future__ import annotations

from openf1._filters import Filter, build_query_params


class TestFilter:
    def test_gt(self) -> None:
        f = Filter(gt=5)
        assert f.to_params("speed") == [("speed>", "5")]

    def test_gte(self) -> None:
        f = Filter(gte=10)
        assert f.to_params("lap_number") == [("lap_number>=", "10")]

    def test_lt(self) -> None:
        f = Filter(lt=100)
        assert f.to_params("speed") == [("speed<", "100")]

    def test_lte(self) -> None:
        f = Filter(lte=50)
        assert f.to_params("lap_number") == [("lap_number<=", "50")]

    def test_range(self) -> None:
        f = Filter(gte=5, lte=10)
        params = f.to_params("lap_number")
        assert ("lap_number>=", "5") in params
        assert ("lap_number<=", "10") in params
        assert len(params) == 2

    def test_all_operators(self) -> None:
        f = Filter(gt=1, gte=2, lt=10, lte=9)
        params = f.to_params("x")
        assert len(params) == 4

    def test_no_operators(self) -> None:
        f = Filter()
        assert f.to_params("key") == []

    def test_float_value(self) -> None:
        f = Filter(gte=1.5)
        assert f.to_params("temp") == [("temp>=", "1.5")]

    def test_string_value(self) -> None:
        f = Filter(gte="2023-01-01")
        assert f.to_params("date") == [("date>=", "2023-01-01")]

    def test_frozen(self) -> None:
        """Filter should be immutable."""
        import pytest

        f = Filter(gte=5)
        with pytest.raises(AttributeError):
            f.gte = 10  # type: ignore[misc]


class TestBuildQueryParams:
    def test_simple_equality(self) -> None:
        params = build_query_params(session_key=9161, driver_number=1)
        assert ("session_key", "9161") in params
        assert ("driver_number", "1") in params

    def test_filter_value(self) -> None:
        params = build_query_params(
            session_key=9161,
            lap_number=Filter(gte=5, lte=10),
        )
        assert ("session_key", "9161") in params
        assert ("lap_number>=", "5") in params
        assert ("lap_number<=", "10") in params

    def test_none_values_skipped(self) -> None:
        params = build_query_params(session_key=9161, driver_number=None)
        assert len(params) == 1
        assert params[0] == ("session_key", "9161")

    def test_empty_params(self) -> None:
        params = build_query_params()
        assert params == []

    def test_mixed_types(self) -> None:
        params = build_query_params(
            session_key=9161,
            speed=Filter(gte=300),
            driver_number=1,
        )
        assert len(params) == 3
