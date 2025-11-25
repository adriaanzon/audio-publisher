import os

from cloudevents.http import from_http
from flask import Flask, request
from google.cloud import storage

from generate_file_listing import generate_file_listing
from normalize import normalize

app = Flask(__name__)

# Get bucket names from environment (required)
SOURCE_BUCKET = os.environ["SOURCE_BUCKET"]
DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]


@app.route("/", methods=["POST"])
def handle_event():
    """Handle CloudEvent from Eventarc triggered by Cloud Storage"""

    # Parse the CloudEvent
    event = from_http(request.headers, request.get_data())

    print(f"Received event: {event['type']}")
    print(f"Event data: {event.data}")

    # Extract bucket and object information
    bucket_name = event.data.get("bucket")
    object_name = event.data.get("name")

    print(f"File uploaded: gs://{bucket_name}/{object_name}")

    # Route to appropriate handler based on bucket
    if bucket_name == SOURCE_BUCKET:
        # New WAV file uploaded - normalize it
        print(f"Normalizing audio file: {object_name}")
        normalize(bucket_name, object_name, DESTINATION_BUCKET)
        return f"Normalized {object_name}", 200

    elif bucket_name == DESTINATION_BUCKET:
        # Ignore index.html and JSON placeholders
        if object_name == "index.html":
            print(f"Ignoring index.html upload to prevent infinite loop")
            return "Ignored index.html", 200

        if object_name.endswith(".json"):
            print(f"Ignoring JSON placeholder: {object_name}")
            return "Ignored placeholder", 200

        # New MP3 file created - regenerate file listing
        print(f"Regenerating file listing after upload of: {object_name}")
        generate_file_listing(DESTINATION_BUCKET)
        return f"Generated file listing", 200

    else:
        print(f"Unknown bucket: {bucket_name}")
        return f"Unknown bucket: {bucket_name}", 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
