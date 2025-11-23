# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Station is an audio upload and processing system for recordings from a Behringer X32 console. It consists of two main components:

1. **Raspberry Pi** (Rust): USB drive watcher that detects flash drives, mounts them, and uploads WAV recordings to Google Cloud Storage
2. **Cloud** (Python): Cloud Run service that processes uploaded recordings using FFmpeg (normalization, silence removal) and generates file listings

## Architecture

### Raspberry Pi Component (`raspberry_pi/`)

- **Main entry**: `src/main.rs` - Requires root privileges to mount USB drives
- **USB Watcher**: `src/usb_drive_watcher.rs` - Monitors udev events for USB partition additions, automatically mounts VFAT drives to `/mnt/{sysname}`
- **Recording Uploader**: `src/recording_uploader.rs`
  - Scans mounted drives for `R_*.wav` files (Behringer X32 format)
  - Tracks uploaded recordings via timestamps in `/var/lib/audio-publisher/uploaded_recordings.txt`
  - On first run, uploads only the latest recording; subsequently uploads all new recordings
  - Cloud upload is currently stubbed out (see `upload_files()`)

### Cloud Component (`cloud/`)

- **Main entry**: `src/main.py` - Flask app that receives Cloud Storage events via Eventarc
- **Normalization**: `src/normalize.py` - Uses FFmpeg to normalize audio to -16dB LUFS and remove silences
- **File Listing**: `src/generate_file_listing.py` - Generates HTML listing of processed recordings

### Infrastructure (`cloud/gcp.tf`)

- **Storage**: Two GCS buckets (source WAV files, normalized MP3 files). Destination bucket is publicly readable for web access.
- **Compute**: Cloud Run service running containerized Flask app with FFmpeg
- **Events**: Eventarc triggers route Cloud Storage object finalization events to Cloud Run
- **IAM**: Service account (`eventarc-cloud-run-invoker`) with roles for invoking Cloud Run and receiving events
- **APIs**: Requires Cloud Build, Eventarc, Cloud Run, Storage, and IAM APIs enabled

## Development Commands

### Raspberry Pi (Rust)

```bash
# Build for aarch64 (Raspberry Pi)
cd raspberry_pi
cargo build --target aarch64-unknown-linux-gnu

# Run locally (requires root)
sudo cargo run
```

The build target is configured in `Cargo.toml` for cross-compilation to ARM64.

### Cloud (Python)

```bash
cd cloud

# Install dependencies with uv
uv sync

# Run locally
uv run python src/main.py

# Build and push Docker image
gcloud builds submit --region=europe-west1 --tag europe-west1-docker.pkg.dev/triple-shadow-457412-j1/terminus/terminus:dev
```

### Infrastructure (Terraform)

```bash
cd cloud

# Initialize Terraform
terraform init

# Plan changes
terraform plan

# Apply infrastructure
terraform apply
```

**Important**: Before running Terraform:
1. Copy `terraform.tfvars.example` to `terraform.tfvars` and configure variables
2. Place service account JSON key at `cloud/service-account.json`
3. Manually enable Cloud Resource Manager API in Google Cloud Console

## Key Implementation Details

### Raspberry Pi
- **USB Detection**: Uses `udev` to detect partition add events, not full device events
- **File System**: Assumes VFAT file system for USB drives (see `usb_drive_watcher.rs:74`)
- **State Tracking**: Recording upload state is maintained in `/var/lib/audio-publisher/uploaded_recordings.txt` using Unix timestamps

### Cloud
- **Event-Driven Architecture**: Two Eventarc triggers watch different buckets (source for normalization, destination for listing generation)
- **FFmpeg Processing**: Audio normalization uses `loudnorm=I=-16` and `silenceremove=stop_periods=-1:stop_duration=10:stop_threshold=-50dB`
- **Temporary Files**: Processing uses `tempfile.TemporaryDirectory()` for download/processing/upload workflow
- **Docker Build**: Multi-stage build using `uv` for dependency management and Alpine for minimal image size
- **Public Access**: Recordings are publicly accessible at `https://storage.googleapis.com/{destination-bucket}/index.html`

### Important Considerations
- **Infrastructure as Code**: ALL infrastructure changes (creating/deleting resources, modifying IAM, bucket configurations, etc.) must be made via Terraform. Read-only operations (`gsutil ls`, `gcloud run services logs`, etc.) and application deployments (building/pushing Docker images, updating service images) are fine to do via CLI tools.
- **Docker Image**: Must be built and pushed before deploying Cloud Run service. Terraform references hardcoded Artifact Registry path.
- **Rate Limiting**: Rapid uploads can trigger GCS rate limits on `index.html` (429 errors). This is expected behavior and doesn't affect functionality.
- **Deployment Order**: 1) Build/push Docker image, 2) Apply Terraform, 3) Update Cloud Run service if image changed
