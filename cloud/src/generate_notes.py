import os
from dataclasses import dataclass
from pathlib import Path

from google.cloud import storage

MAX_AUDIO_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

DEFAULT_PROMPT_FILE = "prompts/sermon.md"
DEFAULT_MODEL = "gemini-2.5-flash-lite"


@dataclass
class SuggestedCut:
    start: str
    end: str

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end}


@dataclass
class Notes:
    title: str | None
    description: str | None
    suggested_cut: SuggestedCut | None

    @classmethod
    def empty(cls) -> "Notes":
        return cls(title=None, description=None, suggested_cut=None)


def is_audio_too_large(blob: storage.Blob) -> bool:
    return blob.size is not None and blob.size > MAX_AUDIO_SIZE_BYTES


def load_prompt() -> str:
    path = os.environ.get("PROMPT_FILE", DEFAULT_PROMPT_FILE)
    return Path(path).read_text()
