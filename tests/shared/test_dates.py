"""Tests for shared.dates.parse_date compact-date support."""
import pytest
from shared.dates import parse_date


def test_compact_iso_date():
    assert parse_date("20270419") == "2027-04-19"


@pytest.mark.parametrize("bad", ["2027419", "20271399", "202704190"])
def test_malformed_compact_dates_return_none(bad):
    assert parse_date(bad) is None
