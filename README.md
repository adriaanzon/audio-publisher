# The Station

Upload station for recordings from an audio console.

<!-- Add a photo here -->

## Compatibility

The Station currently matches file names formats for the following audio consoles:

- Behringer X32: `R_YYYYMMDD-HHMMSS.wav`
- Allen & Heath CQ: `AHCQ/USBREC/CQ-ST001.WAV`

## Deployment

The Station consists of two parts: the physical upload station and the cloud services that process the recordings.

### Cloud

The cloud services are deployed on Google Cloud Platform (GCP) using Terraform.

First of all, you need to configure the variables in `terraform.tfvars` in your local clone of the repository. You can use the [terraform.tfvars.example](terraform.tfvars.example) file as a starting point.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Navigate to IAM & Admin > Service Accounts.
3. Create a new service account or select an existing one.
4. Assign the necessary roles
5. Generate a JSON key for the service account and download it to `cloud/service-account.json` in the repository (this file is git-ignored).

Before running Terraform, manually enable the Cloud Resource Manager API in Google Cloud.

### Raspberry Pi

#### Installing Raspberry Pi OS Lite

The Raspberry Pi should be running Raspberry Pi OS Lite. You can install it using the [Raspberry Pi Imager](https://www.raspberrypi.com/software/).

- When prompted to choose an OS, select "Raspberry Pi OS (other)" > "Raspberry Pi OS Lite (64-bit)".
- In the Customization step, configure:
    - User: Set a username (e.g. `pi`) and password
    - Wi-Fi: Set the SSID and password for your network (if not using Ethernet)
    - Remote access: Enable SSH, and use public key authentication

#### Deploying the watcher

Use `raspberry_pi/deploy.sh` to deploy the current working version of the watcher to the Raspberry Pi. The script uses Ansible to configure Raspberry Pi OS Lite.

## Development

### Previewing the audio file listing

To preview the audio file listing locally, you can use the following command:

```bash
cd cloud
uv run preview_template.py
```

### Building and deploying the Docker image

```bash
cd cloud
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

## License

[GNU Affero General Public License v3.0](LICENSE)
