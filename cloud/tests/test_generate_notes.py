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
