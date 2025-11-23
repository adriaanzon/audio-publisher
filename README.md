# The Station

Upload station for recordings from an audio console.

<!-- Add a photo here -->

## Compatibility

The Station currently only works with recordings from the Behringer X32 console.

## Deployment

The Station consists of two parts: the physical upload station and the cloud services that process the recordings.

### Cloud

The cloud services are deployed on Google Cloud Platform (GCP) using Terraform.

First of all, you need to configure the variables in `terraform.tfvars` in your local clone of the repository. You can use the [terraform.tfvars.example](terraform.tfvars.example) file as a starting point.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Navigate to IAM & Admin > Service Accounts.
3. Create a new service account or select an existing one.
4. Assign the necessary roles
5. Generate a JSON key for the service account and download it to service-account.json in the root of the repository.

Before running Terraform, manually enable the Cloud Resource Manager API in Google Cloud.

#### Previewing the audio file listing

To preview the audio file listing locally, you can use the following command:

```bash
cd cloud
uv run preview_template.py
```

### Raspberry Pi

Use Ansible to deploy the upload station on a Raspberry Pi.

## License

[GNU Affero General Public License v3.0](LICENSE)
