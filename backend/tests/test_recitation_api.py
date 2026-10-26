from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_align_recitation_returns_missing_word():
    response = client.post(
        "/api/v1/recitation/align",
        json={
            "expected_text": "بسم الله الرحمن الرحيم",
            "recognized_text": "بسم الله الرحيم",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["expected_word_count"] == 4
    assert data["recognized_word_count"] == 3
    assert data["matched_word_count"] == 3
    assert len(data["issues"]) == 1

    issue = data["issues"][0]
    assert issue["operation"] == "deletion"
    assert issue["expected_word"] == "الرحمن"
    assert issue["recognized_word"] is None
    assert issue["expected_index"] == 2


def test_align_recitation_with_identical_text():
    text = "بسم الله الرحمن الرحيم"

    response = client.post(
        "/api/v1/recitation/align",
        json={
            "expected_text": text,
            "recognized_text": text,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["matched_word_count"] == 4
    assert data["issues"] == []


def test_align_recitation_rejects_missing_fields():
    response = client.post(
        "/api/v1/recitation/align",
        json={"expected_text": "بسم الله"},
    )

    assert response.status_code == 422


def test_align_recitation_rejects_unexpected_fields():
    response = client.post(
        "/api/v1/recitation/align",
        json={
            "expected_text": "بسم الله",
            "recognized_text": "بسم الله",
            "unexpected": True,
        },
    )

    assert response.status_code == 422


def test_align_recitation_rejects_whitespace_only_expected_text():
    response = client.post(
        "/api/v1/recitation/align",
        json={
            "expected_text": "   \n ",
            "recognized_text": "بسم الله",
        },
    )

    assert response.status_code == 422


def test_align_recitation_with_empty_recognized_text():
    response = client.post(
        "/api/v1/recitation/align",
        json={
            "expected_text": "بسم الله",
            "recognized_text": "",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["expected_word_count"] == 2
    assert data["recognized_word_count"] == 0
    assert data["matched_word_count"] == 0
    assert len(data["issues"]) == 2
    assert all(issue["operation"] == "deletion" for issue in data["issues"])
