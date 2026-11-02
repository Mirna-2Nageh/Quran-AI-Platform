"""Tests for memorization progress calculation."""

from app.services.memorization_progress import calculate_progress


def test_empty_progress():
    result = calculate_progress([])
    assert result["total_plans"] == 0
    assert result["completed_ayahs"] == 0
    assert result["completion_rate"] == 0.0


def test_completed_plan():
    plans = [
        dict(surah_number=1, start_ayah=1, end_ayah=7, status="completed")
    ]
    result = calculate_progress(plans)
    assert result["completed_plans"] == 1
    assert result["unique_planned_ayahs"] == 7
    assert result["completed_ayahs"] == 7
    assert result["completion_rate"] == 100.0


def test_overlapping_plans_do_not_double_count():
    plans = [
        dict(surah_number=2, start_ayah=1, end_ayah=10, status="completed"),
        dict(surah_number=2, start_ayah=6, end_ayah=15, status="active"),
    ]
    result = calculate_progress(plans)
    assert result["total_plans"] == 2
    assert result["unique_planned_ayahs"] == 15
    assert result["completed_ayahs"] == 10
    assert result["completion_rate"] == 66.67


def test_identical_plans_do_not_double_count_ayahs():
    plans = [
        dict(surah_number=1, start_ayah=1, end_ayah=7, status="completed"),
        dict(surah_number=1, start_ayah=1, end_ayah=7, status="active"),
    ]

    result = calculate_progress(plans)

    assert result["total_plans"] == 2
    assert result["completed_plans"] == 1
    assert result["unique_planned_ayahs"] == 7
    assert result["completed_ayahs"] == 7
    assert result["completion_rate"] == 100.0
