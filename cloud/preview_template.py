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
                "name": "R_20250101-000003.mp3",
                "url": None,
                "size": None,
                "updated": datetime.now().isoformat(),
                "status": "processing"
            },
            {
                "name": "R_20250101-000001.mp3",
                "url": "https://storage.googleapis.com/example-bucket/R_20250101-000001.mp3",
                "size": "12.3 MB",
                "updated": "2025-11-23T10:30:00+00:00",
                "status": "ready"
            },
            {
                "name": "R_20250101-000002.mp3",
                "url": "https://storage.googleapis.com/example-bucket/R_20250101-000002.mp3",
                "size": "15.7 MB",
                "updated": "2025-11-23T19:00:00+00:00",
                "status": "ready"
            },
        ],
        generation_time=datetime.now().isoformat()
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
