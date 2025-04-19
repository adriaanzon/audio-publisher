"""
This script is used to preview the file listing template while developing.
"""

from flask import Flask, render_template

app = Flask(__name__, template_folder="templates")


@app.route("/")
def index():
    return render_template(
        "file_listing.html.jinja",
        title="Hello World",
        files=[
            {"name": "file1.mp3", "url": "https://example.com"},
            {"name": "file2.mp3", "url": "https://example.com"},
        ],
    )


if __name__ == "__main__":
    app.run(debug=True)
