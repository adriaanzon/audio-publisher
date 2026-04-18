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
