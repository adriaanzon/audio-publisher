"""
This script is used to preview the file listing template while developing.

Usage:
    uv run preview_template.py

Then open http://localhost:5000 in your browser.
"""

from datetime import datetime

from flask import Flask, render_template

app = Flask(__name__, template_folder="src/templates")


@app.route("/")
def index():
    return render_template(
        "index.html.jinja",
        recordings=[
            {
                "name": "R_20260407-100000.mp3",
                "url": "https://storage.googleapis.com/example-bucket/R_20260407-100000.mp3",
                "size": "28.3 MB",
                "updated": "2026-04-07T10:00:00+00:00",
                "status": "ready",
                "title": "Wat als Jezus toch anders is? | Lukas 24:12-35 | Dennis van der Zee",
                "description": "Een overdenking over de Emmaüsgangers en hoe we Jezus vaak niet herkennen wanneer Hij anders blijkt te zijn dan we verwachten.",
                "suggested_cut": {"start": "00:12:34", "end": "00:58:10"},
                "error_code": None,
            },
            {
                "name": "R_20260330-100000.mp3",
                "url": "https://storage.googleapis.com/example-bucket/R_20260330-100000.mp3",
                "size": "24.1 MB",
                "updated": "2026-03-30T10:00:00+00:00",
                "status": "ready",
                "title": "De farizeër en de tollenaar",
                "description": "Over rechtvaardigheid en schuldbesef in de gelijkenis van de farizeër en de tollenaar.",
                "suggested_cut": None,
                "error_code": None,
            },
            {
                "name": "R_20260420-130000.mp3",
                "url": None,
                "size": None,
                "updated": "2026-04-20T13:00:00+00:00",
                "status": "processing",
                "title": None,
                "description": None,
                "suggested_cut": None,
                "error_code": None,
            },
            {
                "name": "R_20260315-094500.mp3",
                "url": None,
                "size": None,
                "updated": "2026-03-15T09:45:00+00:00",
                "status": "error",
                "title": None,
                "description": None,
                "suggested_cut": None,
                "error_code": "zero_byte_file",
            },
        ],
        generation_time=datetime.now().astimezone().isoformat(),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
