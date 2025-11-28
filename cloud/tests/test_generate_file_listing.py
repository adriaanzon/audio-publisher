import json
from datetime import datetime
from unittest.mock import Mock

from src.generate_file_listing import (
    build_recordings_from_placeholders,
    build_all_recordings,
    parse_processing_status,
)


class TestParseProcessingStatus:
    def test_invalid_json_defaults_to_processing(self):
        mock_blob = Mock()
        mock_blob.download_as_text.return_value = "not valid json"

        status, error_code = parse_processing_status(mock_blob)

        assert status == "processing"
        assert error_code is None


class TestBuildRecordingsFromPlaceholders:
    def test_placeholder_with_existing_mp3_excluded(self):
        mock_json_blob = Mock()
        mock_json_blob.updated = datetime(2025, 1, 15, 10, 30, 0)
        mock_json_blob.download_as_text.return_value = json.dumps({
            "status": "processing"
        })

        mock_mp3_blob = Mock()

        json_files = {"recording.json": mock_json_blob}
        mp3_files = {"recording.mp3": mock_mp3_blob}

        result = build_recordings_from_placeholders(json_files, mp3_files)

        assert len(result) == 0


class TestBuildAllRecordings:
    def test_mixed_sorted_by_updated_desc(self):
        old_mp3_blob = Mock()
        old_mp3_blob.public_url = "https://example.com/old.mp3"
        old_mp3_blob.size = 5_000_000
        old_mp3_blob.updated = datetime(2025, 1, 15, 8, 0, 0)

        new_mp3_blob = Mock()
        new_mp3_blob.public_url = "https://example.com/new.mp3"
        new_mp3_blob.size = 5_000_000
        new_mp3_blob.updated = datetime(2025, 1, 15, 12, 0, 0)

        processing_json_blob = Mock()
        processing_json_blob.updated = datetime(2025, 1, 15, 10, 0, 0)
        processing_json_blob.download_as_text.return_value = json.dumps({
            "status": "processing"
        })

        mp3_files = {
            "old.mp3": old_mp3_blob,
            "new.mp3": new_mp3_blob
        }
        json_files = {
            "processing.json": processing_json_blob
        }

        result = build_all_recordings(mp3_files, json_files)

        assert len(result) == 3
        assert result[0].name == "new.mp3"
        assert result[1].name == "processing.mp3"
        assert result[2].name == "old.mp3"
