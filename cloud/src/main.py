import subprocess

from cloudevents.http import from_http
from flask import Flask, request


from generate_file_listing import generate_file_listing
from normalize import normalize

# see https://github.com/GoogleCloudPlatform/eventarc-samples/blob/main/processing-pipelines/bigquery/chart-creator/python/app.py

app = Flask(__name__)


@app.route("/", methods=["POST"])
def handle_post():

    body = pretty_print_POST(request)
    print(body)

    ffmpeg_version = subprocess.check_output(["ffmpeg", "-version"])
    print(ffmpeg_version)

    return body + "\n" + ffmpeg_version.decode('utf-8'), 200


def pretty_print_POST(req):
    return "{}\r\n{}\r\n\r\n{}".format(
        req.method + " " + req.url,
        "\r\n".join("{}: {}".format(k, v) for k, v in req.headers.items()),
        req.data,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
