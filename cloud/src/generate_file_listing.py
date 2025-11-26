import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from google.cloud import storage
from humanize import naturalsize
from jinja2 import Environment, FileSystemLoader


@dataclass
class Recording:
    """Represents a recording entry in the file listing."""
    name: str
    updated: str
    status: str
    url: str | None = None
    size: str | None = None
    error_code: str | None = None

    def to_template_dict(self) -> dict:
        """Convert to dictionary for Jinja template."""
        return {
            'name': self.name,
            'url': self.url,
            'size': self.size,
            'updated': self.updated,
            'status': self.status,
            'error_code': self.error_code
        }


def list_bucket_files(bucket: storage.Bucket) -> tuple[dict[str, storage.Blob], dict[str, storage.Blob]]:
    """
    List and categorize files in the bucket.

    Returns:
        Tuple of (mp3_files, json_files) as dictionaries mapping filename to blob
    """
    blobs = list(bucket.list_blobs())
    mp3_files = {blob.name: blob for blob in blobs if blob.name.endswith('.mp3')}
    json_files = {
        blob.name: blob
        for blob in blobs
        if blob.name.endswith('.json') and blob.name != 'index.html'
    }

    print(f"Found {len(mp3_files)} MP3 files and {len(json_files)} processing placeholders in gs://{bucket.name}")
    return mp3_files, json_files


def parse_processing_status(json_blob: storage.Blob) -> tuple[str, str | None]:
    """
    Parse status information from a JSON placeholder file.

    Returns:
        Tuple of (status, error_code)
    """
    try:
        json_content = json_blob.download_as_text()
        json_data = json.loads(json_content)
        return json_data.get('status', 'processing'), json_data.get('error_code')
    except Exception:
        return 'processing', None


def build_recordings_from_mp3s(mp3_files: dict[str, storage.Blob]) -> list[Recording]:
    """Build Recording objects from completed MP3 files."""
    return [
        Recording(
            name=name,
            url=blob.public_url,
            size=naturalsize(blob.size),
            updated=blob.updated.isoformat(),
            status='ready'
        )
        for name, blob in mp3_files.items()
    ]


def build_recordings_from_placeholders(
    json_files: dict[str, storage.Blob],
    mp3_files: dict[str, storage.Blob]
) -> list[Recording]:
    """Build Recording objects from JSON placeholders (in-progress or failed)."""
    recordings = []

    for name, blob in json_files.items():
        base_name = name.replace('.json', '')
        mp3_name = f"{base_name}.mp3"

        # Only include if the MP3 doesn't exist yet
        if mp3_name not in mp3_files:
            status, error_code = parse_processing_status(blob)
            recordings.append(Recording(
                name=mp3_name,
                url=None,
                size=None,
                updated=blob.updated.isoformat(),
                status=status,
                error_code=error_code
            ))

    return recordings


def build_all_recordings(
    mp3_files: dict[str, storage.Blob],
    json_files: dict[str, storage.Blob]
) -> list[Recording]:
    """Build complete list of recordings, sorted by update time (newest first)."""
    recordings = build_recordings_from_mp3s(mp3_files)
    recordings.extend(build_recordings_from_placeholders(json_files, mp3_files))
    recordings.sort(key=lambda r: r.updated, reverse=True)
    return recordings


def render_listing_page(recordings: list[Recording]) -> str:
    """Render the HTML listing page using Jinja template."""
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("index.html.jinja")

    return template.render(
        recordings=[r.to_template_dict() for r in recordings],
        generation_time=datetime.now().astimezone().isoformat()
    )


def upload_listing_page(bucket: storage.Bucket, html_content: str):
    """Upload the rendered HTML to the bucket with no-cache headers."""
    index_blob = bucket.blob('index.html')
    index_blob.cache_control = 'no-cache, no-store, must-revalidate'
    index_blob.upload_from_string(html_content, content_type='text/html')
    print(f"Uploaded index.html to gs://{bucket.name}/index.html")


def generate_file_listing(bucket_name: str):
    """
    Generates a static HTML listing of all MP3 files in the bucket and uploads it.

    Args:
        bucket_name: Name of the GCS bucket to list files from
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # List and categorize files
    mp3_files, json_files = list_bucket_files(bucket)

    # Build recording entries
    recordings = build_all_recordings(mp3_files, json_files)

    # Render and upload
    html_content = render_listing_page(recordings)
    upload_listing_page(bucket, html_content)
