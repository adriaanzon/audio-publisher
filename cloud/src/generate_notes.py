import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import storage

MAX_AUDIO_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

DEFAULT_PROMPT_FILE = "prompts/sermon.md"
DEFAULT_MODEL = "gemini-2.5-flash"


@dataclass
class SuggestedCut:
    start: int  # seconds from start of recording
    end: int

    def to_dict(self) -> dict:
        return {"start": _format_hms(self.start), "end": _format_hms(self.end)}


def _format_hms(total_seconds: int) -> str:
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


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


import json
import logging
import tempfile
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING", "nullable": True},
        "description": {"type": "STRING", "nullable": True},
        "suggested_cut": {
            "type": "OBJECT",
            "nullable": True,
            "properties": {
                "start": {"type": "INTEGER"},
                "end": {"type": "INTEGER"},
            },
            "required": ["start", "end"],
        },
    },
    "required": ["title", "description", "suggested_cut"],
}


def _build_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


def _parse_notes(raw: str) -> Notes:
    data = json.loads(raw)
    cut_data = data.get("suggested_cut")
    cut = (
        SuggestedCut(start=cut_data["start"], end=cut_data["end"]) if cut_data else None
    )
    return Notes(
        title=data.get("title"),
        description=data.get("description"),
        suggested_cut=cut,
    )


def generate_notes(mp3_blob: storage.Blob) -> Notes:
    """
    Generate AI notes for an MP3 blob. All failures return Notes.empty().
    """
    if is_audio_too_large(mp3_blob):
        logger.info(
            "Skipping notes: %s is %.1f MB (limit %.0f MB)",
            mp3_blob.name,
            (mp3_blob.size or 0) / 1024 / 1024,
            MAX_AUDIO_SIZE_BYTES / 1024 / 1024,
        )
        return Notes.empty()

    uploaded = None
    client = None
    try:
        client = _build_client()
        prompt = load_prompt()

        with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
            tmp.write(mp3_blob.download_as_bytes())
            tmp.flush()
            uploaded = client.files.upload(file=tmp.name)

        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=[uploaded, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )
        if response.text is None:
            raise ValueError("Gemini returned no text")
        return _parse_notes(response.text)
    except Exception:
        logger.exception("Notes generation failed for %s", mp3_blob.name)
        return Notes.empty()
    finally:
        if client is not None and uploaded is not None and uploaded.name is not None:
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                logger.exception("Failed to delete uploaded Gemini file")


def write_ready_json(bucket: storage.Bucket, base_name: str, notes: Notes) -> None:
    """Overwrite `{base_name}.json` in the destination bucket with a `ready` payload."""
    payload = {
        "status": "ready",
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": notes.title,
        "description": notes.description,
        "suggested_cut": notes.suggested_cut.to_dict() if notes.suggested_cut else None,
    }
    blob = bucket.blob(f"{base_name}.json")
    blob.upload_from_string(json.dumps(payload), content_type="application/json")
