from datetime import datetime
from pathlib import Path

from google.cloud import storage
from jinja2 import Environment, FileSystemLoader


def generate_file_listing(bucket_name: str):
    """
    Generates a static HTML listing of all MP3 files in the bucket and uploads it.

    Args:
        bucket_name: Name of the GCS bucket to list files from
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # List all MP3 and JSON files in the bucket
    blobs = list(bucket.list_blobs())
    mp3_files = {blob.name: blob for blob in blobs if blob.name.endswith('.mp3')}
    json_files = {blob.name: blob for blob in blobs if blob.name.endswith('.json') and blob.name != 'index.html'}

    print(f"Found {len(mp3_files)} MP3 files and {len(json_files)} processing placeholders in gs://{bucket_name}")

    # Prepare data for template - combine MP3s and processing files
    recordings = []

    # Add completed MP3 files
    for name, blob in mp3_files.items():
        recordings.append({
            'name': name,
            'url': blob.public_url,
            'size': format_bytes(blob.size),
            'updated': blob.updated.isoformat(),
            'status': 'ready'
        })

    # Add files still being processed (have JSON but no MP3)
    for name, blob in json_files.items():
        base_name = name.replace('.json', '')
        mp3_name = base_name + '.mp3'
        if mp3_name not in mp3_files:
            recordings.append({
                'name': mp3_name,
                'url': None,
                'size': None,
                'updated': blob.updated.isoformat(),
                'status': 'processing'
            })

    # Sort by update time, newest first
    recordings.sort(key=lambda r: r['updated'], reverse=True)

    # Render HTML from template file
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("index.html.jinja")
    html_content = template.render(
        recordings=recordings,
        generation_time=datetime.now().isoformat()
    )

    # Upload index.html to bucket with no-cache headers
    index_blob = bucket.blob('index.html')
    index_blob.cache_control = 'no-cache, no-store, must-revalidate'
    index_blob.upload_from_string(html_content, content_type='text/html')

    print(f"Uploaded index.html to gs://{bucket_name}/index.html")


def format_bytes(size: int) -> str:
    """Format bytes as human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"
