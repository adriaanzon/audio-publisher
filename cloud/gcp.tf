# https://cloud.google.com/functions/docs/tutorials/terraform
# https://cloud.google.com/functions/docs/tutorials/terraform-pubsub maybe here I can find how to trigger the function when a file is uploaded to a bucket

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.8.0"
    }
  }
}

variable "gcp_project" {
  description = "The Google Cloud Platform project ID"
  type        = string
}

variable "gcp_region" {
  description = "The Google Cloud Platform region"
  type        = string
}

variable "gcp_bucket_location" {
  description = "The two-letter location code for the bucket"
  type        = string
}

variable "gcp_bucket_prefix" {
  description = "The name used for the buckets"
  type        = string
}

variable "docker_image" {
  description = "The Docker image for the Cloud Run service"
  type        = string
  default     = "docker.io/adriaanzon/audio-publisher:latest"
}

variable "gemini_api_key" {
  description = "Gemini Developer API key for AI-generated notes"
  type        = string
  sensitive   = true
}

provider "google" {
  project     = var.gcp_project
  region      = var.gcp_region
  credentials = file("service-account.json")
}

resource "google_project_service" "enable_apis" {
  for_each = toset([
    "eventarc.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "secretmanager.googleapis.com",
  ])

  project = var.gcp_project
  service = each.key
}

resource "google_storage_bucket" "destination" {
  name                        = "${var.gcp_bucket_prefix}-normalized" # Every bucket name must be globally unique
  location                    = var.gcp_region
  uniform_bucket_level_access = true
}
resource "google_storage_bucket" "source" {
  name                        = "${var.gcp_bucket_prefix}-wav-source" # Every bucket name must be globally unique
  location                    = var.gcp_region
  uniform_bucket_level_access = true
}

# Make destination bucket publicly readable for the HTML listing and MP3 files
resource "google_storage_bucket_iam_member" "destination_public_read" {
  bucket = google_storage_bucket.destination.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# Service account for Eventarc to invoke Cloud Run
resource "google_service_account" "eventarc_invoker" {
  account_id   = "eventarc-cloud-run-invoker"
  display_name = "Eventarc Cloud Run Invoker"
}

# Allow Eventarc service account to invoke Cloud Run
resource "google_cloud_run_v2_service_iam_member" "eventarc_invoker" {
  name     = google_cloud_run_v2_service.default.name
  location = google_cloud_run_v2_service.default.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.eventarc_invoker.email}"
}

# Allow Eventarc service account to receive events
resource "google_project_iam_member" "eventarc_event_receiver" {
  project = var.gcp_project
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc_invoker.email}"
}

# Allow Cloud Storage service account to publish events to Eventarc
data "google_storage_project_service_account" "gcs_account" {
  project = var.gcp_project
}

resource "google_project_iam_member" "gcs_pubsub_publishing" {
  project = var.gcp_project
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"
  replication {
    auto {}
  }

  depends_on = [google_project_service.enable_apis]
}

resource "google_secret_manager_secret_version" "gemini_api_key" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key
}

# Cloud Run uses the default compute service account unless otherwise configured.
# Grant it access to read the secret.
data "google_project" "current" {
  project_id = var.gcp_project
}

resource "google_secret_manager_secret_iam_member" "cloud_run_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

# Image is built and pushed to GHCR by the GitHub Actions release workflow
resource "google_cloud_run_v2_service" "default" {
  name     = "terminus"
  location = var.gcp_region

  template {
    timeout = "900s"  # 15 minutes

    containers {
      image = var.docker_image

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "SOURCE_BUCKET"
        value = google_storage_bucket.source.name
      }

      env {
        name  = "DESTINATION_BUCKET"
        value = google_storage_bucket.destination.name
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "PROMPT_FILE"
        value = "prompts/sermon.md"
      }
    }
  }

  depends_on = [google_secret_manager_secret_iam_member.cloud_run_access]
}

# Create Eventarc triggers, routing Cloud Storage events to Cloud Run
# https://cloud.google.com/eventarc/docs/creating-triggers-terraform
resource "google_eventarc_trigger" "normalize" {
  name     = "trigger-normalize-incoming-mp3"
  location = var.gcp_region

  # Capture objects changed in the bucket
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.source.name
  }
  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.default.name
      region  = google_cloud_run_v2_service.default.location
    }
  }

  service_account = google_service_account.eventarc_invoker.email

  depends_on = [
    google_cloud_run_v2_service_iam_member.eventarc_invoker,
    google_project_iam_member.eventarc_event_receiver,
    google_project_iam_member.gcs_pubsub_publishing
  ]
}

resource "google_eventarc_trigger" "generate_file_listing" {
  name     = "trigger-generate-file-listing"
  location = var.gcp_region

  # Capture objects changed in the bucket
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.destination.name
  }

  # Send events to the Cloud Run service
  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.default.name
      region  = google_cloud_run_v2_service.default.location
    }
  }

  service_account = google_service_account.eventarc_invoker.email

  depends_on = [
    google_cloud_run_v2_service_iam_member.eventarc_invoker,
    google_project_iam_member.eventarc_event_receiver,
    google_project_iam_member.gcs_pubsub_publishing
  ]
}

# Update PubSub subscriptions created by Eventarc to configure ack deadline
# This prevents duplicate event processing due to the default 10s timeout
# Using null_resource because Terraform doesn't support managing Eventarc subscriptions directly
# https://github.com/hashicorp/terraform-provider-google/issues/17701
resource "null_resource" "update_normalize_subscription_ack" {
  # Set ack deadline to 10 minutes (600s) to match Cloud Run timeout
  # Default 10s causes duplicate processing for long-running FFmpeg tasks
  provisioner "local-exec" {
    command = <<-EOT
      SUBSCRIPTION=$(gcloud pubsub subscriptions list \
        --filter="name~eventarc-${var.gcp_region}-${google_eventarc_trigger.normalize.name}-sub" \
        --format="value(name)" | head -1)
      gcloud pubsub subscriptions update $SUBSCRIPTION --ack-deadline=600
    EOT
  }

  depends_on = [google_eventarc_trigger.normalize]

  # Re-run if trigger is recreated
  triggers = {
    trigger_id = google_eventarc_trigger.normalize.id
  }
}

resource "null_resource" "update_file_listing_subscription_ack" {
  provisioner "local-exec" {
    command = <<-EOT
      SUBSCRIPTION=$(gcloud pubsub subscriptions list \
        --filter="name~eventarc-${var.gcp_region}-${google_eventarc_trigger.generate_file_listing.name}-sub" \
        --format="value(name)" | head -1)
      gcloud pubsub subscriptions update $SUBSCRIPTION --ack-deadline=600
    EOT
  }

  depends_on = [google_eventarc_trigger.generate_file_listing]

  triggers = {
    trigger_id = google_eventarc_trigger.generate_file_listing.id
  }
}
