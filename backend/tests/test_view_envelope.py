#!/usr/bin/env python3
"""
Vision — View Envelope Validator Tests.

Tests the validate_view_envelope function against valid fixtures and
common mutation scenarios.

Usage:
    cd backend && python -m pytest tests/test_view_envelope.py -v
    cd backend && python tests/test_view_envelope.py
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

# Ensure backend/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schemas.view_envelope import validate_view_envelope

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_FIXTURES_PATH = (
    Path(__file__).resolve().parents[2]
    / "context-engine"
    / "specs"
    / "dynamic-view-system"
    / "02-fixtures.json"
)

with open(_FIXTURES_PATH) as f:
    FIXTURES = json.load(f)

VALID_ENVELOPE = FIXTURES[0]  # Credit report analysis — composite view


# ---------------------------------------------------------------------------
# Valid content
# ---------------------------------------------------------------------------

def test_valid_envelope_passes():
    """The canonical fixture must validate."""
    valid, error = validate_view_envelope(VALID_ENVELOPE)
    assert valid is True, f"Expected valid, got: {error}"
    assert error is None


def test_second_fixture_passes():
    """The bank statement fixture must also validate."""
    valid, error = validate_view_envelope(FIXTURES[1])
    assert valid is True, f"Expected valid, got: {error}"


def test_single_view_passes():
    """An envelope with a single view (not composite) must validate."""
    single = deepcopy(VALID_ENVELOPE)
    single["views"] = [single["views"][0]]  # just the cards view
    valid, error = validate_view_envelope(single)
    assert valid is True, f"Expected valid single-view envelope, got: {error}"


def test_minimal_envelope_passes():
    """An envelope with only required fields must validate."""
    minimal = {
        "documentMetadata": {"title": "Test"},
        "views": [
            {
                "viewType": "cards",
                "title": "Summary",
                "data": {"pairs": [{"key": "Count", "value": "3"}]},
            }
        ],
    }
    valid, error = validate_view_envelope(minimal)
    assert valid is True, f"Expected valid minimal envelope, got: {error}"


# ---------------------------------------------------------------------------
# Invalid: structural
# ---------------------------------------------------------------------------

def test_none_rejected():
    valid, error = validate_view_envelope(None)
    assert valid is False
    assert "null" in error.lower()


def test_list_rejected():
    valid, error = validate_view_envelope([{"documentMetadata": {}, "views": []}])
    assert valid is False
    assert "not an array" in error.lower() or "object" in error.lower()


def test_string_rejected():
    valid, error = validate_view_envelope("not an envelope")
    assert valid is False
    assert "object" in error.lower()


# ---------------------------------------------------------------------------
# Invalid: missing required fields
# ---------------------------------------------------------------------------

def test_missing_document_metadata():
    bad = deepcopy(VALID_ENVELOPE)
    del bad["documentMetadata"]
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None
    assert "documentMetadata" in error


def test_missing_views():
    bad = deepcopy(VALID_ENVELOPE)
    del bad["views"]
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None
    assert "views" in error


def test_empty_views_array():
    bad = deepcopy(VALID_ENVELOPE)
    bad["views"] = []
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None


def test_missing_view_title():
    bad = deepcopy(VALID_ENVELOPE)
    del bad["views"][0]["title"]
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None
    assert "title" in error


def test_unknown_view_type():
    bad = deepcopy(VALID_ENVELOPE)
    bad["views"][0]["viewType"] = "chart"  # not in v1 enum
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None
    # The error should mention the invalid value or the enum constraint
    assert "chart" in error or "viewType" in error


# ---------------------------------------------------------------------------
# Invalid: view-specific schema violations
# ---------------------------------------------------------------------------

def test_table_missing_headers():
    bad = deepcopy(VALID_ENVELOPE)
    table_view = bad["views"][1]  # the table view
    del table_view["data"]["headers"]
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None
    assert "headers" in error


def test_table_missing_rows():
    bad = deepcopy(VALID_ENVELOPE)
    table_view = bad["views"][1]
    del table_view["data"]["rows"]
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None
    assert "rows" in error


def test_table_row_missing_id():
    bad = deepcopy(VALID_ENVELOPE)
    table_view = bad["views"][1]
    del table_view["data"]["rows"][0]["id"]
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None
    assert "id" in error


def test_list_missing_list_style():
    bad = deepcopy(VALID_ENVELOPE)
    list_view = bad["views"][2]  # the list view
    del list_view["data"]["listStyle"]
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None
    assert "listStyle" in error


def test_list_invalid_style():
    bad = deepcopy(VALID_ENVELOPE)
    bad["views"][2]["data"]["listStyle"] = "toggle"  # not in enum
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None


def test_cards_missing_pairs():
    bad = deepcopy(VALID_ENVELOPE)
    cards_view = bad["views"][0]  # the cards view
    del cards_view["data"]["pairs"]
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None
    assert "pairs" in error


def test_cards_pair_missing_key():
    bad = deepcopy(VALID_ENVELOPE)
    del bad["views"][0]["data"]["pairs"][0]["key"]
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None
    assert "key" in error


def test_cards_invalid_emphasis():
    bad = deepcopy(VALID_ENVELOPE)
    bad["views"][0]["data"]["pairs"][0]["emphasis"] = "critical"  # not in enum
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None


def test_empty_headers_array():
    bad = deepcopy(VALID_ENVELOPE)
    bad["views"][1]["data"]["headers"] = []
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None


def test_empty_items_array():
    bad = deepcopy(VALID_ENVELOPE)
    bad["views"][2]["data"]["items"] = []
    valid, error = validate_view_envelope(bad)
    assert valid is False
    assert error is not None


# ---------------------------------------------------------------------------
# Chart view tests
# ---------------------------------------------------------------------------

def test_chart_bar_passes():
    """Bar chart with valid data must validate."""
    chart_view = {
        "viewType": "chart",
        "title": "Account Balances",
        "data": {
            "chartType": "bar",
            "headers": ["Account Name", "Balance"],
            "rows": [
                {"id": "1", "Account Name": "Chase", "Balance": "4230"},
                {"id": "2", "Account Name": "Wells Fargo", "Balance": "1150"},
            ],
        },
    }
    env = {
        "documentMetadata": {"title": "Chart Test"},
        "views": [chart_view],
    }
    valid, error = validate_view_envelope(env)
    assert valid is True, f"Expected valid bar chart, got: {error}"


def test_chart_line_passes():
    """Line chart with valid data must validate."""
    env = {
        "documentMetadata": {"title": "Chart Test"},
        "views": [
            {
                "viewType": "chart",
                "title": "Monthly Trend",
                "data": {
                    "chartType": "line",
                    "headers": ["Month", "Revenue"],
                    "rows": [
                        {"id": "1", "Month": "Jan", "Revenue": "10000"},
                        {"id": "2", "Month": "Feb", "Revenue": "12000"},
                    ],
                },
            }
        ],
    }
    valid, error = validate_view_envelope(env)
    assert valid is True, f"Expected valid line chart, got: {error}"


def test_chart_pie_passes():
    """Pie chart with valid data must validate."""
    env = {
        "documentMetadata": {"title": "Chart Test"},
        "views": [
            {
                "viewType": "chart",
                "title": "Market Share",
                "data": {
                    "chartType": "pie",
                    "headers": ["Company", "Share"],
                    "rows": [
                        {"id": "1", "Company": "Acme", "Share": "45"},
                        {"id": "2", "Company": "Globex", "Share": "30"},
                    ],
                },
            }
        ],
    }
    valid, error = validate_view_envelope(env)
    assert valid is True, f"Expected valid pie chart, got: {error}"


def test_chart_missing_chart_type():
    """Chart view missing chartType must fail."""
    chart = {
        "viewType": "chart",
        "title": "Test",
        "data": {
            "headers": ["A", "B"],
            "rows": [{"id": "1", "A": "x", "B": "10"}],
        },
    }
    env = {"documentMetadata": {"title": "Test"}, "views": [chart]}
    valid, error = validate_view_envelope(env)
    assert valid is False
    assert error is not None
    assert "chartType" in error


def test_chart_invalid_chart_type():
    """Chart with unknown chartType must fail."""
    chart = {
        "viewType": "chart",
        "title": "Test",
        "data": {
            "chartType": "scatter",
            "headers": ["A", "B"],
            "rows": [{"id": "1", "A": "x", "B": "10"}],
        },
    }
    env = {"documentMetadata": {"title": "Test"}, "views": [chart]}
    valid, error = validate_view_envelope(env)
    assert valid is False
    assert error is not None


def test_chart_missing_headers():
    """Chart missing headers must fail."""
    chart = {
        "viewType": "chart",
        "title": "Test",
        "data": {
            "chartType": "bar",
            "rows": [{"id": "1", "A": "x"}],
        },
    }
    env = {"documentMetadata": {"title": "Test"}, "views": [chart]}
    valid, error = validate_view_envelope(env)
    assert valid is False
    assert error is not None
    assert "headers" in error


def test_chart_missing_rows():
    """Chart missing rows must fail."""
    chart = {
        "viewType": "chart",
        "title": "Test",
        "data": {
            "chartType": "bar",
            "headers": ["A", "B"],
        },
    }
    env = {"documentMetadata": {"title": "Test"}, "views": [chart]}
    valid, error = validate_view_envelope(env)
    assert valid is False
    assert error is not None
    assert "rows" in error


# ---------------------------------------------------------------------------
# Main — run without pytest
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import traceback

    tests = [
        fn for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  PASS  {test_fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {test_fn.__name__}: {exc}")
        except Exception:
            failed += 1
            print(f"  ERROR {test_fn.__name__}:")
            traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    sys.exit(0 if failed == 0 else 1)
