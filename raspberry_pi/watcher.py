import os
import subprocess
from pathlib import Path

import pyudev
from google.cloud import storage

from logger import ConsoleLogger
from raspberry_pi.flash_drive_reader import X32FlashDriveReader

# Watches raspberry pi USB ports for newly attached flash drives and uploads the latest recording to cloud bucket


flash_drive_reader = X32FlashDriveReader()
logger = ConsoleLogger()
var_path = os.path.dirname(os.path.realpath(__file__)) + '/var'


def watch():
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="block")

    for device in iter(monitor.poll, None):
        if device.action == "add" and device.device_type == "partition":
            mount_point = "/mnt/" + device.sys_name
            Path(mount_point).mkdir(parents=True, exist_ok=True)
            subprocess.run(["mount", device.device_node, mount_point])

            recording = flash_drive_reader.get_latest_recording(Path(mount_point))

            if recording and not has_been_uploaded(recording):
                upload_recording(recording)
                mark_as_uploaded(recording)

            subprocess.run(["umount", mount_point])


def upload_recording(recording: Path):
    client = storage.Client().from_service_account_json() # TODO


def has_been_uploaded(path):
    with open(var_path + "/uploaded_recordings", "r") as file:
        return path.name + "\n" in file.readlines()


def mark_as_uploaded(path):
    with open(var_path + "/uploaded_recordings", "a") as file:
        file.write(path.name + "\n")

    logger.info(path.name + " has been uploaded.")


if __name__ == "__main__":
    if os.geteuid() != 0:
        exit("In order to mount the USB drive, root priviliges are required. Try running the command using sudo.")

    Path(var_path).mkdir(parents=True, exist_ok=True)
    Path(var_path + "/uploaded_recordings").touch(exist_ok=True)

    watch()
