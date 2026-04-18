import json
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def buckets(monkeypatch):
    monkeypatch.setenv("SOURCE_BUCKET", "src-bucket")
    monkeypatch.setenv("DESTINATION_BUCKET", "dst-bucket")


def _event(bucket: str, name: str) -> dict:
    return {
        "type": "google.cloud.storage.object.v1.finalized",
        "bucket": bucket,
        "name": name,
    }


class TestDestinationMp3Routing:
    def test_mp3_with_ready_json_skips_notes(self, monkeypatch):
        import importlib
        from src import main

        importlib.reload(main)  # pick up env vars

        ready_payload = {
            "status": "ready",
            "title": "t",
            "description": "d",
            "suggested_cut": None,
        }
        ready_blob = Mock()
        ready_blob.exists.return_value = True
        ready_blob.download_as_text.return_value = json.dumps(ready_payload)

        bucket = Mock()
        bucket.blob.return_value = ready_blob
        client = Mock()
        client.bucket.return_value = bucket

        monkeypatch.setattr(main, "_storage_client", lambda: client)
        gen_notes = Mock()
        write_ready = Mock()
        gen_listing = Mock()
        monkeypatch.setattr(main, "generate_notes", gen_notes)
        monkeypatch.setattr(main, "write_ready_json", write_ready)
        monkeypatch.setattr(main, "generate_file_listing", gen_listing)

        main.handle_destination_mp3("R_20260418.mp3")

        gen_notes.assert_not_called()
        write_ready.assert_not_called()
        gen_listing.assert_called_once_with("dst-bucket")

    def test_mp3_with_processing_json_runs_notes(self, monkeypatch):
        import importlib
        from src import main
        from src.generate_notes import Notes, SuggestedCut

        importlib.reload(main)

        processing_blob = Mock()
        processing_blob.exists.return_value = True
        processing_blob.download_as_text.return_value = json.dumps(
            {"status": "processing"}
        )
        mp3_blob = Mock()
        mp3_blob.size = 50_000_000

        bucket = Mock()
        bucket.blob.side_effect = lambda name: (
            processing_blob if name.endswith(".json") else mp3_blob
        )
        client = Mock()
        client.bucket.return_value = bucket

        notes = Notes(title="t", description="d", suggested_cut=None)
        gen_notes = Mock(return_value=notes)
        write_ready = Mock()
        gen_listing = Mock()

        monkeypatch.setattr(main, "_storage_client", lambda: client)
        monkeypatch.setattr(main, "generate_notes", gen_notes)
        monkeypatch.setattr(main, "write_ready_json", write_ready)
        monkeypatch.setattr(main, "generate_file_listing", gen_listing)

        main.handle_destination_mp3("R_20260418.mp3")

        gen_notes.assert_called_once_with(mp3_blob)
        write_ready.assert_called_once_with(bucket, "R_20260418", notes)
        gen_listing.assert_called_once_with("dst-bucket")

    def test_mp3_with_missing_json_runs_notes(self, monkeypatch):
        """Migration re-upload path: MP3 present, JSON absent."""
        import importlib
        from src import main
        from src.generate_notes import Notes

        importlib.reload(main)

        missing_json_blob = Mock()
        missing_json_blob.exists.return_value = False
        mp3_blob = Mock()
        mp3_blob.size = 50_000_000

        bucket = Mock()
        bucket.blob.side_effect = lambda name: (
            missing_json_blob if name.endswith(".json") else mp3_blob
        )
        client = Mock()
        client.bucket.return_value = bucket

        notes = Notes.empty()
        gen_notes = Mock(return_value=notes)
        write_ready = Mock()
        gen_listing = Mock()

        monkeypatch.setattr(main, "_storage_client", lambda: client)
        monkeypatch.setattr(main, "generate_notes", gen_notes)
        monkeypatch.setattr(main, "write_ready_json", write_ready)
        monkeypatch.setattr(main, "generate_file_listing", gen_listing)

        main.handle_destination_mp3("R_20260418.mp3")

        gen_notes.assert_called_once_with(mp3_blob)
        write_ready.assert_called_once_with(bucket, "R_20260418", notes)
        gen_listing.assert_called_once_with("dst-bucket")
