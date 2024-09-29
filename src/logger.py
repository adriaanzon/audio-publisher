from abc import ABC, abstractmethod


class Logger(ABC):
    @abstractmethod
    def info(self, message: str):
        pass

    @abstractmethod
    def warning(self, message: str):
        pass


class LogStack(Logger):
    def __init__(self, loggers: list[Logger]):
        self.loggers = loggers

    def info(self, message: str):
        map(lambda logger: logger.info(message), self.loggers)

    def warning(self, message: str):
        map(lambda logger: logger.warning(message), self.loggers)


class TextLogger(Logger):
    @abstractmethod
    def write(self, message: str):
        pass

    def info(self, message: str):
        self.write("INFO: " + message)

    def warning(self, message: str):
        self.write("WARNING: " + message)


class ConsoleLogger(TextLogger):
    def write(self, message: str):
        print(message)


class FileLogger(TextLogger):
    def write(self, message: str):
        pass


class SlackLogger(Logger):
    def info(self, message: str):
        pass

    def warning(self, message: str):
        pass


class EmailLogger(Logger):
    def info(self, message: str):
        pass

    def warning(self, message: str):
        pass
