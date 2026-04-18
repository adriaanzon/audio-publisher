import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from google.cloud import storage
from humanize import naturalsize
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


@dataclass
class Recording:
    name: str
    updated: str
    status: str
    url: str | None = None
    size: str | None = None
    error_code: str | None = None
    title: str | None = None
    description: str | None = None
    suggested_cut: dict | None = None

    def to_template_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "size": self.size,
            "updated": self.updated,
            "status": self.status,
            "error_code": self.error_code,
            "title": self.title,
            "description": self.description,
            "suggested_cut": self.suggested_cut,
        }


def list_bucket_files(
    bucket: storage.Bucket,
) -> tuple[dict[str, storage.Blob], dict[str, storage.Blob]]:
    blobs = list(bucket.list_blobs())
    mp3_files = {b.name: b for b in blobs if b.name.endswith(".mp3")}
    json_files = {
        b.name: b for b in blobs if b.name.endswith(".json") and b.name != "index.html"
    }
    logger.info(
        "Found %d MP3 files and %d JSON files in gs://%s",
        len(mp3_files),
        len(json_files),
        bucket.name,
    )
    return mp3_files, json_files


def _parse_json_payload(blob: storage.Blob) -> dict:
    try:
        return json.loads(blob.download_as_text())
    except Exception:
        return {"status": "processing"}


def build_recordings(
    json_files: dict[str, storage.Blob],
    mp3_files: dict[str, storage.Blob],
) -> list[Recording]:
    """Iterate over JSON blobs, pairing each with its MP3 by base name.
    MP3s without a paired JSON are skipped (migration handles them)."""
    recordings: list[Recording] = []

    for json_name, json_blob in json_files.items():
        base = json_name[: -len(".json")]
        mp3_name = f"{base}.mp3"
        mp3_blob = mp3_files.get(mp3_name)
        payload = _parse_json_payload(json_blob)
        status = payload.get("status", "processing")

        if status == "ready" and mp3_blob is None:
            logger.warning(
                "JSON %s is ready but %s is missing — skipping", json_name, mp3_name
            )
            continue

        recording = Recording(
            name=mp3_name,
            updated=json_blob.updated.isoformat() if json_blob.updated else "",
            status=status,
            error_code=payload.get("error_code"),
            title=payload.get("title"),
            description=payload.get("description"),
            suggested_cut=payload.get("suggested_cut"),
        )
        if mp3_blob is not None:
            recording.url = mp3_blob.public_url
            if mp3_blob.size is not None:
                recording.size = naturalsize(mp3_blob.size)
        recordings.append(recording)

    orphan_mp3s = [
        name for name in mp3_files if name.replace(".mp3", ".json") not in json_files
    ]
    for name in orphan_mp3s:
        logger.warning(
            "MP3 %s has no paired JSON — skipping (see Migration in the spec)", name
        )

    recordings.sort(key=lambda r: r.updated, reverse=True)
    return recordings


def render_listing_page(recordings: list[Recording]) -> str:
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("index.html.jinja")
    return template.render(
        recordings=[r.to_template_dict() for r in recordings],
        generation_time=datetime.now().astimezone().isoformat(),
    )


def upload_listing_page(bucket: storage.Bucket, html_content: str):
    index_blob = bucket.blob("index.html")
    index_blob.cache_control = "no-cache, no-store, must-revalidate"
    index_blob.upload_from_string(html_content, content_type="text/html")
    logger.info("Uploaded index.html to gs://%s/index.html", bucket.name)


def generate_file_listing(bucket_name: str):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    mp3_files, json_files = list_bucket_files(bucket)
    recordings = build_recordings(json_files, mp3_files)
    html_content = render_listing_page(recordings)
    upload_listing_page(bucket, html_content)
