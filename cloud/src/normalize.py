import json
import subprocess
import tempfile
from datetime import datetime
from os.path import basename, splitext
from pathlib import Path

from google.cloud import storage


def normalize(source_bucket: str, source_object: str, destination_bucket: str) -> str:
    """
    Download WAV file from Cloud Storage, normalize it with FFmpeg, and upload the MP3 result.

    Args:
        source_bucket: Name of the GCS bucket containing the source WAV file
        source_object: Object name (path) of the source WAV file
        destination_bucket: Name of the GCS bucket to upload the normalized MP3

    Returns:
        The object name of the uploaded MP3 file
    """
    storage_client = storage.Client()

    # Check if output already exists or is being processed (idempotency check)
    base_name = splitext(basename(source_object))[0]
    output_filename = base_name + ".mp3"
    placeholder_filename = base_name + ".json"

    destination_bucket_obj = storage_client.bucket(destination_bucket)
    destination_blob = destination_bucket_obj.blob(output_filename)
    placeholder_blob = destination_bucket_obj.blob(placeholder_filename)

    if destination_blob.exists():
        print(f"Output already exists: gs://{destination_bucket}/{output_filename} - skipping processing")
        return output_filename

    if placeholder_blob.exists():
        print(f"Processing already in progress: gs://{destination_bucket}/{placeholder_filename} - skipping duplicate")
        return output_filename

    # Create placeholder file to indicate processing has started
    print(f"Creating processing placeholder: gs://{destination_bucket}/{placeholder_filename}")
    placeholder_data = {
        "status": "processing",
        "source_file": source_object,
        "started_at": datetime.utcnow().isoformat() + "Z"
    }
    placeholder_blob.upload_from_string(json.dumps(placeholder_data), content_type="application/json")

    # Create temporary files for processing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download source WAV file
        source_path = Path(tmpdir) / "source.wav"
        print(f"Downloading gs://{source_bucket}/{source_object} to {source_path}")

        bucket = storage_client.bucket(source_bucket)
        blob = bucket.blob(source_object)
        blob.download_to_filename(source_path)

        # Generate output path
        output_path = Path(tmpdir) / output_filename

        # Run FFmpeg normalization
        print(f"Normalizing audio: {source_path} -> {output_path}")
        subprocess.run(
            [
                "ffmpeg",
                "-i", str(source_path),
                # Normalize loudness to -16dB LUFS and remove long silences
                "-af", "loudnorm=I=-16,silenceremove=stop_periods=-1:stop_duration=10:stop_threshold=-50dB",
                str(output_path),
            ],
            check=True
        )

        # Upload normalized MP3 to destination bucket
        print(f"Uploading {output_path} to gs://{destination_bucket}/{output_filename}")
        destination_blob.upload_from_filename(output_path)

        # Delete placeholder file now that processing is complete
        print(f"Deleting placeholder: gs://{destination_bucket}/{placeholder_filename}")
        placeholder_blob.delete()

        # Delete source WAV file after successful conversion
        print(f"Deleting source file: gs://{source_bucket}/{source_object}")
        blob.delete()

        print(f"Successfully normalized and uploaded: gs://{destination_bucket}/{output_filename}")
        return output_filename
