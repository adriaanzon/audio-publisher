from unittest.mock import Mock

from src.generate_notes import (
    MAX_AUDIO_SIZE_BYTES,
    Notes,
    SuggestedCut,
    is_audio_too_large,
)


class TestSuggestedCut:
    def test_to_dict(self):
        cut = SuggestedCut(start="00:05:00", end="00:45:30")
        assert cut.to_dict() == {"start": "00:05:00", "end": "00:45:30"}


class TestNotes:
    def test_all_null(self):
        notes = Notes(title=None, description=None, suggested_cut=None)
        assert notes.title is None
        assert notes.description is None
        assert notes.suggested_cut is None

    def test_with_values(self):
        cut = SuggestedCut(start="00:10:00", end="01:00:00")
        notes = Notes(
            title="Gods Genade | 1 Korintiërs 1:1-9",
            description="Over de genade van God.",
            suggested_cut=cut,
        )
        assert notes.title.startswith("Gods Genade")
        assert notes.suggested_cut.start == "00:10:00"


class TestIsAudioTooLarge:
    def test_at_limit_is_not_too_large(self):
        blob = Mock()
        blob.size = MAX_AUDIO_SIZE_BYTES
        assert is_audio_too_large(blob) is False

    def test_over_limit_is_too_large(self):
        blob = Mock()
        blob.size = MAX_AUDIO_SIZE_BYTES + 1
        assert is_audio_too_large(blob) is True

    def test_under_limit_is_not_too_large(self):
        blob = Mock()
        blob.size = 50 * 1024 * 1024
        assert is_audio_too_large(blob) is False


class TestLoadPrompt:
    def test_reads_file_contents(self, tmp_path, monkeypatch):
        from src.generate_notes import load_prompt

        prompt_file = tmp_path / "my_prompt.md"
        prompt_file.write_text("Be concise.")

        monkeypatch.setenv("PROMPT_FILE", str(prompt_file))
        assert load_prompt() == "Be concise."

    def test_default_path_used_when_env_unset(self, tmp_path, monkeypatch):
        from src.generate_notes import load_prompt

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "sermon.md").write_text("Default prompt.")

        monkeypatch.delenv("PROMPT_FILE", raising=False)
        monkeypatch.chdir(tmp_path)

        assert load_prompt() == "Default prompt."


import json as _json

import pytest


class TestGenerateNotes:
    def _blob(self, size=1_000_000):
        blob = Mock()
        blob.name = "R_20260418.mp3"
        blob.size = size
        blob.download_as_bytes.return_value = b"fake-mp3-bytes"
        return blob

    def test_returns_empty_when_blob_too_large(self, monkeypatch):
        from src import generate_notes

        blob = self._blob(size=MAX_AUDIO_SIZE_BYTES + 1)
        client_factory = Mock(side_effect=AssertionError("should not be called"))
        monkeypatch.setattr(generate_notes, "_build_client", client_factory)

        result = generate_notes.generate_notes(blob)

        assert result == Notes.empty()
        client_factory.assert_not_called()

    def test_returns_empty_when_api_key_missing(self, monkeypatch):
        from src import generate_notes

        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        blob = self._blob()

        result = generate_notes.generate_notes(blob)

        assert result == Notes.empty()

    def test_returns_parsed_notes_on_success(self, monkeypatch, tmp_path):
        from src import generate_notes

        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        prompt_file = tmp_path / "sermon.md"
        prompt_file.write_text("Prompt text")
        monkeypatch.setenv("PROMPT_FILE", str(prompt_file))

        uploaded = Mock(name="uploaded-file")
        response = Mock()
        response.text = _json.dumps({
            "title": "Gods Genade | 1 Korintiërs 1:1-9 | Dennis",
            "description": "Over de genade van God.",
            "suggested_cut": {"start": "00:10:00", "end": "01:00:00"},
        })

        fake_client = Mock()
        fake_client.files.upload.return_value = uploaded
        fake_client.models.generate_content.return_value = response
        monkeypatch.setattr(generate_notes, "_build_client", lambda: fake_client)

        blob = self._blob()
        result = generate_notes.generate_notes(blob)

        assert result.title.startswith("Gods Genade")
        assert result.description == "Over de genade van God."
        assert result.suggested_cut == SuggestedCut(start="00:10:00", end="01:00:00")
        fake_client.files.delete.assert_called_once_with(name=uploaded.name)

    def test_returns_empty_on_api_exception(self, monkeypatch, tmp_path):
        from src import generate_notes

        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        prompt_file = tmp_path / "sermon.md"
        prompt_file.write_text("Prompt text")
        monkeypatch.setenv("PROMPT_FILE", str(prompt_file))

        fake_client = Mock()
        fake_client.files.upload.side_effect = RuntimeError("boom")
        monkeypatch.setattr(generate_notes, "_build_client", lambda: fake_client)

        blob = self._blob()
        result = generate_notes.generate_notes(blob)

        assert result == Notes.empty()

    def test_returns_empty_on_malformed_response(self, monkeypatch, tmp_path):
        from src import generate_notes

        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        prompt_file = tmp_path / "sermon.md"
        prompt_file.write_text("Prompt text")
        monkeypatch.setenv("PROMPT_FILE", str(prompt_file))

        response = Mock()
        response.text = "not-json"

        fake_client = Mock()
        fake_client.files.upload.return_value = Mock(name="uploaded")
        fake_client.models.generate_content.return_value = response
        monkeypatch.setattr(generate_notes, "_build_client", lambda: fake_client)

        blob = self._blob()
        result = generate_notes.generate_notes(blob)

        assert result == Notes.empty()

    def test_returns_empty_with_null_fields_pass_through(self, monkeypatch, tmp_path):
        from src import generate_notes

        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        prompt_file = tmp_path / "sermon.md"
        prompt_file.write_text("Prompt text")
        monkeypatch.setenv("PROMPT_FILE", str(prompt_file))

        response = Mock()
        response.text = _json.dumps({
            "title": None,
            "description": None,
            "suggested_cut": None,
        })

        fake_client = Mock()
        fake_client.files.upload.return_value = Mock(name="uploaded")
        fake_client.models.generate_content.return_value = response
        monkeypatch.setattr(generate_notes, "_build_client", lambda: fake_client)

        blob = self._blob()
        result = generate_notes.generate_notes(blob)

        assert result == Notes.empty()


class TestWriteReadyJson:
    def test_writes_ready_status_with_notes(self):
        from src.generate_notes import write_ready_json

        bucket = Mock()
        json_blob = Mock()
        bucket.blob.return_value = json_blob

        notes = Notes(
            title="T | ref | speaker",
            description="desc",
            suggested_cut=SuggestedCut(start="00:05:00", end="00:45:00"),
        )
        write_ready_json(bucket, "R_20260418-120000", notes)

        bucket.blob.assert_called_once_with("R_20260418-120000.json")
        uploaded_json_str = json_blob.upload_from_string.call_args.args[0]
        payload = _json.loads(uploaded_json_str)

        assert payload["status"] == "ready"
        assert payload["title"] == "T | ref | speaker"
        assert payload["description"] == "desc"
        assert payload["suggested_cut"] == {"start": "00:05:00", "end": "00:45:00"}
        assert "completed_at" in payload

    def test_writes_nulls_when_notes_empty(self):
        from src.generate_notes import write_ready_json

        bucket = Mock()
        json_blob = Mock()
        bucket.blob.return_value = json_blob

        write_ready_json(bucket, "R_20260418-120000", Notes.empty())

        uploaded = _json.loads(json_blob.upload_from_string.call_args.args[0])
        assert uploaded["status"] == "ready"
        assert uploaded["title"] is None
        assert uploaded["description"] is None
        assert uploaded["suggested_cut"] is None
