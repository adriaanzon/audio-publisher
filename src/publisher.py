from abc import ABC, abstractmethod

from storage import StoredFile


class Publisher(ABC):
    @abstractmethod
    def publish(self, file: StoredFile) -> str:
        pass


class EmailPublisher(Publisher):
    def publish(self, file: StoredFile) -> str:
        pass
