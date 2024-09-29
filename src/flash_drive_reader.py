from abc import ABC, abstractmethod
from pathlib import Path


class FlashDriveReader(ABC):
    @abstractmethod
    def get_latest_recording(self, mount_point: Path) -> Path:
        pass


class X32FlashDriveReader(FlashDriveReader):
    def get_latest_recording(self, mount_point: Path) -> Path:
        files = mount_point.glob("R_*.wav")

        latest_recording = max(files, key=lambda x: x.stat().st_ctime) if files else None

        # TODO: If the size of the file is 0 bytes, it means that the recording was not saved properly.
        #  In this case, the system administrator must be warned to recover the recording.

        return latest_recording
