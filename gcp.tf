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

variable gcp_project {
  description = "The Google Cloud Platform project ID"
  type = string
}

variable gcp_region {
  description = "The Google Cloud Platform region"
  type = string
}

variable gcp_bucket_location {
  description = "The two-letter location code for the bucket"
  type = string
}

variable gcp_bucket_prefix {
  description = "The name used for the buckets"
  type = string
}

provider "google" {
  project = var.gcp_project
  region = var.gcp_region
  credentials = file("service-account.json")
}
resource "google_storage_bucket" "functions" {
  name = "${var.gcp_bucket_prefix}-gcf-source" # Every bucket name must be globally unique
  location = var.gcp_bucket_location
  uniform_bucket_level_access = true
}
resource "google_storage_bucket" "destination" {
  name = "${var.gcp_bucket_prefix}-normalized" # Every bucket name must be globally unique
  location = var.gcp_bucket_location
  uniform_bucket_level_access = true
}
resource "google_storage_bucket" "source" {
  name = "${var.gcp_bucket_prefix}-wav-source" # Every bucket name must be globally unique
  location = var.gcp_bucket_location
  uniform_bucket_level_access = true
}


data "archive_file" "default" {
  type = "zip"
  output_path = "/tmp/function-source.zip"
  source_dir = "cloud/functions/"
}
resource "google_storage_bucket_object" "object" {
  name = "function-source.zip"
  bucket = google_storage_bucket.functions.name
  source = data.archive_file.default.output_path # Add path to the zipped function source code
}

# TODO: instead of google_cloudfunctions2_function use the newer replacement
resource "google_cloudfunctions2_function" "normalize" {
  name = "normalize"
  location = "europe-west4"
  description = "Normalize an audio file that was uploaded to a Cloud Storage bucket"

  build_config {
    runtime = "python312"
    entry_point = "normalize"
    source {
      storage_source {
        bucket = google_storage_bucket.functions.name
        object = google_storage_bucket_object.object.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    available_memory = "256M"
    timeout_seconds = 600
  }
}

resource "google_cloudfunctions2_function" "generate_file_listing" {
    name = "generate-file-listing"
    location = "europe-west4"
    description = "Generate a file listing of the preken bucket"

    build_config {
        runtime = "python312"
        entry_point = "generate_file_listing"
        source {
        storage_source {
            bucket = google_storage_bucket.functions.name
            object = google_storage_bucket_object.object.name
        }
        }
    }

    service_config {
        max_instance_count = 1
        available_memory = "256M"
        timeout_seconds = 600
    }
}

resource "google_cloud_run_service_iam_member" "normalize_member" {
  location = google_cloudfunctions2_function.normalize.location
  service = google_cloudfunctions2_function.normalize.name
  role = "roles/run.invoker"
  member = "allUsers"
}

output "normalize_function_uri" {
  value = google_cloudfunctions2_function.normalize.service_config[0].uri
}

# Create Eventarcs trigger, routing Cloud Storage events to Cloud Run
resource "google_eventarc_trigger" "normalize" {
  name = "trigger-normalize-incoming-mp3"
  location = google_cloudfunctions2_function.normalize.location

  # Capture objects changed in the bucket
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.source.name
  }

  # Send events to the function
  destination {
    cloud_run_service {
      service = google_cloudfunctions2_function.normalize.name
      region  = google_cloudfunctions2_function.normalize.location
    }
  }
}

resource "google_eventarc_trigger" "generate_file_listing" {
    name = "trigger-generate-file-listing"
    location = google_cloudfunctions2_function.generate_file_listing.location

    # Capture objects changed in the bucket
    matching_criteria {
        attribute = "type"
        value     = "google.cloud.storage.object.v1.finalized"
    }
    matching_criteria {
        attribute = "bucket"
        value     = google_storage_bucket.destination.name
    }

    # Send events to the function
    destination {
        cloud_run_service {
            service = google_cloudfunctions2_function.generate_file_listing.name
            region  = google_cloudfunctions2_function.generate_file_listing.location
        }
    }
}
