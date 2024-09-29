from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import boto3


@dataclass
class StoredFile:
    name: str
    url: str


class Storage(ABC):
    @abstractmethod
    def store(self, file_path: Path) -> StoredFile:
        pass

    @abstractmethod
    def publishes(self) -> bool:
        """
        Whether this storage disk publishes the file to the recipients. When
        false, the application will take on responsibility to send an email
        with the link to the stored file.
        """
        pass


class S3Storage(Storage):
    def store(self, file_path: Path) -> StoredFile:
        # Implementation details for AWS S3
        pass

    def publishes(self) -> bool:
        return False


class SharePointStorage(Storage):
    def store(self, file_path: Path) -> StoredFile:
        # Implementation details for SharePoint
        pass

    def publishes(self) -> bool:
        return True
