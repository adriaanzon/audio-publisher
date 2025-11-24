# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See also the main @README.md for overall project context.

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

#### Infrastructure (`raspberry_pi/ansible/`)

- Uses Ansible to configure Raspberry Pi OS Lite
- Any secrets should be read from Terraform files to reduce duplication. Do not hardcode secrets like credentials or bucket names in Ansible playbooks, as it is important to keep any potentially sensitive information out of version control.

### Cloud Component (`cloud/`)

- **Main entry**: `src/main.py` - Flask app that receives Cloud Storage events via Eventarc
- **Normalization**: `src/normalize.py` - Uses FFmpeg to normalize audio to -16dB LUFS and remove silences
- **File Listing**: `src/generate_file_listing.py` - Generates HTML listing of processed recordings

#### Considerations

- **Infrastructure as Code**: ALL infrastructure changes (creating/deleting resources, modifying IAM, bucket configurations, etc.) must be made via Terraform. Read-only operations (`gsutil ls`, `gcloud run services logs`, etc.) and application deployments (building/pushing Docker images, updating service images) are fine to do via CLI tools. Do not hardcode credentials or resource names in application code; use environment variables or Terraform-managed secrets.
- **Docker Image**: Must be built and pushed before deploying Cloud Run service. Terraform references hardcoded Artifact Registry path.
- **Deployment Order**: 1) Build/push Docker image, 2) Apply Terraform, 3) Update Cloud Run service if image changed
- **Public Access**: Recordings are publicly accessible at `https://storage.googleapis.com/{destination-bucket}/index.html`

#### Infrastructure (`cloud/gcp.tf`)

- **Storage**: Two GCS buckets (source WAV files, normalized MP3 files). Destination bucket is publicly readable for web access.
- **Compute**: Cloud Run service running containerized Flask app with FFmpeg
- **Events**: Eventarc triggers route Cloud Storage object finalization events to Cloud Run
- **IAM**: Service account (`eventarc-cloud-run-invoker`) with roles for invoking Cloud Run and receiving events
- **APIs**: Requires Cloud Build, Eventarc, Cloud Run, Storage, and IAM APIs enabled
