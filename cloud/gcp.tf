# https://cloud.google.com/functions/docs/tutorials/terraform
# https://cloud.google.com/functions/docs/tutorials/terraform-pubsub maybe here I can find how to trigger the function when a file is uploaded to a bucket

terraform {
    required_providers {
        google = {
            source = "hashicorp/google"
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

resource "google_project_service" "enable_apis" {
    for_each = toset([
        "cloudbuild.googleapis.com",
        "eventarc.googleapis.com",
        "run.googleapis.com",
        "storage.googleapis.com",
    ])

    project = var.gcp_project
    service = each.key
}

resource "google_storage_bucket" "functions" {
    name = "${var.gcp_bucket_prefix}-gcf-source" # Every bucket name must be globally unique
    location = var.gcp_region
    uniform_bucket_level_access = true
}
resource "google_storage_bucket" "destination" {
    name = "${var.gcp_bucket_prefix}-normalized" # Every bucket name must be globally unique
    location = var.gcp_region
    uniform_bucket_level_access = true
}
resource "google_storage_bucket" "source" {
    name = "${var.gcp_bucket_prefix}-wav-source" # Every bucket name must be globally unique
    location = var.gcp_region
    uniform_bucket_level_access = true
}


# https://cloud.google.com/build/docs/build-push-docker-image
# Image is built using `gcloud builds submit --region=europe-west1 --tag europe-west1-docker.pkg.dev/triple-shadow-457412-j1/terminus/terminus:dev` from the cloud directory
# Later publish the image to GitHub Packages when open-sourcing the project
resource "google_cloud_run_v2_service" "default" {
    name = "terminus"
    location = var.gcp_region

    template {
        containers {
            image = "europe-west1-docker.pkg.dev/triple-shadow-457412-j1/terminus/terminus:dev"
        }
    }
}

# Create Eventarcs trigger, routing Cloud Storage events to Cloud Run
# https://cloud.google.com/eventarc/docs/creating-triggers-terraform
# TODO: Add Eventarc service account for the buckets
resource "google_eventarc_trigger" "normalize" {
    name = "trigger-normalize-incoming-mp3"
    location = var.gcp_region

    # Capture objects changed in the bucket
    matching_criteria {
        attribute = "type"
        value = "google.cloud.storage.object.v1.finalized"
    }
    matching_criteria {
        attribute = "bucket"
        value = google_storage_bucket.source.name
    }
    destination {
        cloud_run_service {
            service = google_cloud_run_v2_service.default.name
            region = google_cloud_run_v2_service.default.location
        }
    }
}

resource "google_eventarc_trigger" "generate_file_listing" {
    name = "trigger-generate-file-listing"
    location = var.gcp_region

    # Capture objects changed in the bucket
    matching_criteria {
        attribute = "type"
        value = "google.cloud.storage.object.v1.finalized"
    }
    matching_criteria {
        attribute = "bucket"
        value = google_storage_bucket.destination.name
    }

    # Send events to the Cloud Run service
    destination {
        cloud_run_service {
            service = google_cloud_run_v2_service.default.name
            region = google_cloud_run_v2_service.default.location
        }
    }
}
