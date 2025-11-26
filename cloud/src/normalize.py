import json
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from os.path import basename, splitext
from pathlib import Path

from google.cloud import storage


class ProcessingStatus(Enum):
    ALREADY_COMPLETE = "already_complete"
    IN_PROGRESS = "in_progress"
    READY_TO_PROCESS = "ready_to_process"


@dataclass
class ProcessingJob:
    """Represents a normalization job with all necessary paths and identifiers."""
    source_bucket: str
    source_object: str
    destination_bucket: str
    base_name: str
    output_filename: str
    placeholder_filename: str

    @classmethod
    def from_source(cls, source_bucket: str, source_object: str, destination_bucket: str):
        base_name = splitext(basename(source_object))[0]
        return cls(
            source_bucket=source_bucket,
            source_object=source_object,
            destination_bucket=destination_bucket,
            base_name=base_name,
            output_filename=f"{base_name}.mp3",
            placeholder_filename=f"{base_name}.json"
        )


def check_processing_status(job: ProcessingJob, storage_client: storage.Client) -> ProcessingStatus:
    """Check if the file has already been processed or is currently being processed."""
    bucket = storage_client.bucket(job.destination_bucket)
    output_blob = bucket.blob(job.output_filename)
    placeholder_blob = bucket.blob(job.placeholder_filename)

    if output_blob.exists():
        print(f"Output already exists: gs://{job.destination_bucket}/{job.output_filename} - skipping processing")
        return ProcessingStatus.ALREADY_COMPLETE

    if placeholder_blob.exists():
        print(f"Processing already in progress: gs://{job.destination_bucket}/{job.placeholder_filename} - skipping duplicate")
        return ProcessingStatus.IN_PROGRESS

    return ProcessingStatus.READY_TO_PROCESS


def create_processing_placeholder(job: ProcessingJob, storage_client: storage.Client):
    """Create a JSON placeholder file to indicate processing has started."""
    bucket = storage_client.bucket(job.destination_bucket)
    placeholder_blob = bucket.blob(job.placeholder_filename)

    print(f"Creating processing placeholder: gs://{job.destination_bucket}/{job.placeholder_filename}")
    placeholder_data = {
        "status": "processing",
        "source_file": job.source_object,
        "started_at": datetime.utcnow().isoformat() + "Z"
    }
    placeholder_blob.upload_from_string(json.dumps(placeholder_data), content_type="application/json")


def mark_processing_failed(job: ProcessingJob, error_code: str, storage_client: storage.Client):
    """Update the placeholder with error information."""
    bucket = storage_client.bucket(job.destination_bucket)
    placeholder_blob = bucket.blob(job.placeholder_filename)

    print(f"ERROR: Marking job as failed with error_code={error_code}")
    error_data = {
        "status": "error",
        "error_code": error_code,
        "source_file": job.source_object,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "failed_at": datetime.utcnow().isoformat() + "Z"
    }
    placeholder_blob.upload_from_string(json.dumps(error_data), content_type="application/json")
    print(f"Updated placeholder with error status: gs://{job.destination_bucket}/{job.placeholder_filename}")


def download_source_file(job: ProcessingJob, destination_path: Path, storage_client: storage.Client):
    """Download the source WAV file from GCS to local disk."""
    print(f"Downloading gs://{job.source_bucket}/{job.source_object} to {destination_path}")
    bucket = storage_client.bucket(job.source_bucket)
    blob = bucket.blob(job.source_object)
    blob.download_to_filename(destination_path)


def normalize_audio_file(source_path: Path, output_path: Path):
    """Run FFmpeg to normalize audio loudness and remove silences."""
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


def upload_result_and_cleanup(job: ProcessingJob, output_path: Path, storage_client: storage.Client):
    """Upload the normalized MP3 and delete temporary files."""
    bucket = storage_client.bucket(job.destination_bucket)

    # Upload MP3
    output_blob = bucket.blob(job.output_filename)
    print(f"Uploading {output_path} to gs://{job.destination_bucket}/{job.output_filename}")
    output_blob.upload_from_filename(output_path)

    # Delete placeholder
    placeholder_blob = bucket.blob(job.placeholder_filename)
    print(f"Deleting placeholder: gs://{job.destination_bucket}/{job.placeholder_filename}")
    placeholder_blob.delete()

    # Delete source WAV
    source_bucket = storage_client.bucket(job.source_bucket)
    source_blob = source_bucket.blob(job.source_object)
    print(f"Deleting source file: gs://{job.source_bucket}/{job.source_object}")
    source_blob.delete()

    print(f"Successfully normalized and uploaded: gs://{job.destination_bucket}/{job.output_filename}")


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
    job = ProcessingJob.from_source(source_bucket, source_object, destination_bucket)

    # Check if already processed or in progress
    status = check_processing_status(job, storage_client)
    if status != ProcessingStatus.READY_TO_PROCESS:
        return job.output_filename

    # Mark as processing
    create_processing_placeholder(job, storage_client)

    # Process in temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "source.wav"
        download_source_file(job, source_path, storage_client)

        # Validate file size
        if source_path.stat().st_size == 0:
            print(f"ERROR: Source file is 0 bytes (corrupted): gs://{source_bucket}/{source_object}")
            mark_processing_failed(job, "zero_byte_file", storage_client)
            # Don't delete source file - might want to investigate
            return job.output_filename

        # Normalize audio
        output_path = Path(tmpdir) / job.output_filename
        normalize_audio_file(source_path, output_path)

        # Upload and cleanup
        upload_result_and_cleanup(job, output_path, storage_client)

    return job.output_filename
