import json
import os

from cloudevents.http import from_http
from flask import Flask, request
from google.cloud import storage

from generate_file_listing import generate_file_listing
from generate_notes import generate_notes, write_ready_json
from normalize import normalize

app = Flask(__name__)

SOURCE_BUCKET = os.environ["SOURCE_BUCKET"]
DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]


def _storage_client() -> storage.Client:
    return storage.Client()


def _json_status(bucket: storage.Bucket, base_name: str) -> str | None:
    blob = bucket.blob(f"{base_name}.json")
    if not blob.exists():
        return None
    try:
        return json.loads(blob.download_as_text()).get("status")
    except Exception:
        return None


def handle_destination_mp3(object_name: str) -> None:
    """Run notes generation when a destination-bucket MP3 isn't already `ready`,
    then always regenerate the listing."""
    base_name = object_name[:-len(".mp3")]
    client = _storage_client()
    bucket = client.bucket(DESTINATION_BUCKET)

    status = _json_status(bucket, base_name)
    if status == "ready":
        print(f"{object_name}: JSON already ready, skipping notes generation")
    else:
        mp3_blob = bucket.blob(object_name)
        notes = generate_notes(mp3_blob)
        write_ready_json(bucket, base_name, notes)

    generate_file_listing(DESTINATION_BUCKET)


@app.route("/", methods=["POST"])
def handle_event():
    event = from_http(request.headers, request.get_data())
    print(f"Received event: {event['type']}")
    print(f"Event data: {event.data}")

    bucket_name = event.data.get("bucket")
    object_name = event.data.get("name")

    print(f"File uploaded: gs://{bucket_name}/{object_name}")

    if bucket_name == SOURCE_BUCKET:
        print(f"Normalizing audio file: {object_name}")
        normalize(bucket_name, object_name, DESTINATION_BUCKET)
        return f"Normalized {object_name}", 200

    if bucket_name == DESTINATION_BUCKET:
        if object_name == "index.html":
            print("Ignoring index.html upload to prevent infinite loop")
            return "Ignored index.html", 200

        if object_name.endswith(".mp3"):
            print(f"Processing MP3 upload: {object_name}")
            handle_destination_mp3(object_name)
            return f"Handled MP3 {object_name}", 200

        print(f"Regenerating file listing after upload of: {object_name}")
        generate_file_listing(DESTINATION_BUCKET)
        return "Generated file listing", 200

    print(f"Unknown bucket: {bucket_name}")
    return f"Unknown bucket: {bucket_name}", 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
