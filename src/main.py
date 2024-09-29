import os
import subprocess
from pathlib import Path

import pyudev

from flash_drive_reader import X32FlashDriveReader
from logger import ConsoleLogger
from raspberrypi.normalize import normalize
from raspberrypi.publisher import EmailPublisher
from storage import S3Storage

flash_drive_reader = X32FlashDriveReader()
storage = S3Storage()
publisher = EmailPublisher()
logger = ConsoleLogger()
var_path = os.path.dirname(os.path.realpath(__file__)) + '/../var'


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

            if recording and not has_been_processed(recording):
                process_recording(recording)
                mark_as_processed(recording)

            subprocess.run(["umount", mount_point])


def process_recording(recording: Path):
    normalized_recording = normalize(recording)
    stored_file = storage.store(normalized_recording)

    if not storage.publishes():
        publisher.publish(stored_file)


def has_been_processed(path):
    with open(var_path + "/processed_recordings", "r") as file:
        return path.name + "\n" in file.readlines()


def mark_as_processed(path):
    with open(var_path + "/processed_recordings", "a") as file:
        file.write(path.name + "\n")

    logger.info(path.name + " has been processed.")


if __name__ == "__main__":
    if os.geteuid() != 0:
        exit("In order to mount the USB drive, root priviliges are required. Try running the command using sudo.")

    Path(var_path).mkdir(parents=True, exist_ok=True)
    Path(var_path + "/processed_recordings").touch(exist_ok=True)

    watch()
