#!/bin/bash
set -e

# Deployment script for Raspberry Pi audio uploader

# Check if vars.yml exists
if [ ! -f "ansible/vars.yml" ]; then
    echo "Error: ansible/vars.yml not found"
    echo "Copy ansible/vars.yml.example to ansible/vars.yml and fill in your values"
    exit 1
fi

echo "Building for Raspberry Pi (ARM64)..."
cross build --release --target aarch64-unknown-linux-gnu

echo "Deploying with Ansible..."
cd ansible
ansible-playbook playbook.yml "$@"

echo ""
echo "Deployment complete!"
