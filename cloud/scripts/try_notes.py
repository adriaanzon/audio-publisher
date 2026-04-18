"""Run generate_notes against a local MP3 file for manual testing.

Usage:
    GEMINI_API_KEY=... uv run python scripts/try_notes.py path/to/sermon.mp3
"""

import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from generate_notes import generate_notes


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1

    mp3_path = Path(sys.argv[1])
    if not mp3_path.is_file():
        print(f"Not a file: {mp3_path}")
        return 1

    data = mp3_path.read_bytes()
    blob = Mock()
    blob.name = mp3_path.name
    blob.size = len(data)
    blob.download_as_bytes.return_value = data

    notes = generate_notes(blob)
    print(f"title:         {notes.title}")
    print(f"description:   {notes.description}")
    print(f"suggested_cut: {notes.suggested_cut}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
