import json
from datetime import datetime
from unittest.mock import Mock

from src.generate_file_listing import (
    Recording,
    build_recordings,
)


def _json_blob(name: str, payload: dict, updated: datetime):
    blob = Mock()
    blob.name = name
    blob.download_as_text.return_value = json.dumps(payload)
    blob.updated = updated
    return blob


def _mp3_blob(name: str, size: int, updated: datetime, url: str):
    blob = Mock()
    blob.name = name
    blob.size = size
    blob.updated = updated
    blob.public_url = url
    return blob


class TestBuildRecordings:
    def test_ready_json_with_mp3_produces_full_recording(self):
        json_b = _json_blob(
            "R_1.json",
            {
                "status": "ready",
                "title": "Wat als Jezus toch anders is? | Lukas 24 | Dennis",
                "description": "Korte beschrijving.",
                "suggested_cut": {"start": "00:10:00", "end": "00:55:00"},
            },
            updated=datetime(2026, 4, 7, 10, 0, 0),
        )
        mp3_b = _mp3_blob(
            "R_1.mp3", 12_300_000, datetime(2026, 4, 7, 9, 55, 0), "https://e/R_1.mp3"
        )

        result = build_recordings({"R_1.json": json_b}, {"R_1.mp3": mp3_b})

        assert len(result) == 1
        r = result[0]
        assert r.status == "ready"
        assert r.name == "R_1.mp3"
        assert r.url == "https://e/R_1.mp3"
        assert r.title.startswith("Wat als")
        assert r.description == "Korte beschrijving."
        assert r.suggested_cut == {"start": "00:10:00", "end": "00:55:00"}

    def test_processing_json_without_mp3(self):
        json_b = _json_blob(
            "R_1.json", {"status": "processing"}, datetime(2026, 4, 7, 10, 0, 0)
        )

        result = build_recordings({"R_1.json": json_b}, {})

        assert len(result) == 1
        assert result[0].status == "processing"
        assert result[0].url is None

    def test_error_json_is_rendered(self):
        json_b = _json_blob(
            "R_1.json",
            {"status": "error", "error_code": "zero_byte_file"},
            datetime(2026, 4, 7, 10, 0, 0),
        )

        result = build_recordings({"R_1.json": json_b}, {})

        assert len(result) == 1
        assert result[0].status == "error"
        assert result[0].error_code == "zero_byte_file"

    def test_orphan_mp3_is_skipped(self):
        mp3_b = _mp3_blob(
            "R_1.mp3", 1, datetime(2026, 4, 7, 10, 0, 0), "https://e/R_1.mp3"
        )

        result = build_recordings({}, {"R_1.mp3": mp3_b})

        assert result == []

    def test_ready_json_without_mp3_is_skipped(self):
        """Edge case: JSON says ready but the MP3 blob vanished. Treat as inconsistent, skip."""
        json_b = _json_blob(
            "R_1.json",
            {
                "status": "ready",
                "title": "t",
                "description": "d",
                "suggested_cut": None,
            },
            datetime(2026, 4, 7, 10, 0, 0),
        )

        result = build_recordings({"R_1.json": json_b}, {})

        assert result == []

    def test_sorted_by_updated_desc(self):
        older = _json_blob(
            "R_old.json",
            {
                "status": "ready",
                "title": "t",
                "description": "d",
                "suggested_cut": None,
            },
            updated=datetime(2026, 4, 1, 10, 0, 0),
        )
        newer = _json_blob(
            "R_new.json",
            {
                "status": "ready",
                "title": "t",
                "description": "d",
                "suggested_cut": None,
            },
            updated=datetime(2026, 4, 7, 10, 0, 0),
        )
        old_mp3 = _mp3_blob(
            "R_old.mp3", 1, datetime(2026, 4, 1, 9, 59), "https://e/old"
        )
        new_mp3 = _mp3_blob(
            "R_new.mp3", 1, datetime(2026, 4, 7, 9, 59), "https://e/new"
        )

        result = build_recordings(
            {"R_old.json": older, "R_new.json": newer},
            {"R_old.mp3": old_mp3, "R_new.mp3": new_mp3},
        )

        assert [r.name for r in result] == ["R_new.mp3", "R_old.mp3"]
