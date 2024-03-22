import codecs
import os
import sys
import time
import unicodedata
from contextlib import contextmanager
from queue import Empty, Queue
from typing import Any, Dict, Iterator
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl

from colorama import Fore, Style


class BaseLogger:
    def __init__(self) -> None:
        self._print_serial_logs = True
        self.logger = Logger()

    def set_logging_type(self, log_type: str) -> None:
        if log_type == "junit-xml":
            self.logger = JunitXMLLogger()  # type: ignore
        else:
            self.logger = Logger()  # type: ignore

    def info(self, *args, **kwargs) -> None:  # type: ignore
        self.logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs) -> None:  # type: ignore
        self.logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs) -> None:  # type: ignore
        self.logger.error(*args, **kwargs)

    @contextmanager
    def nested(self, message: str, attributes: Dict[str, str] = {}) -> Iterator[None]:
        return self.logger.nested(message, attributes)

    @contextmanager
    def subtest(self, message: str, attributes: Dict[str, str] = {}) -> Iterator[None]:
        return self.logger.subtest(message, attributes)

    def log(self, message: str, attributes: Dict[str, str] = {}) -> None:
        self.logger.log(message, attributes)

    def log_serial(self, message: str, machine: str) -> None:
        self.logger.log_serial(message, machine)


class Logger:
    def __init__(self) -> None:
        self.logfile = os.environ.get("LOGFILE", "/dev/null")
        self.logfile_handle = codecs.open(self.logfile, "wb")
        self.xml = XMLGenerator(self.logfile_handle, encoding="utf-8")
        self.queue: "Queue[Dict[str, str]]" = Queue()

        self.xml.startDocument()
        self.xml.startElement("logfile", attrs=AttributesImpl({}))

        self._print_serial_logs = True

    @staticmethod
    def _eprint(*args: object, **kwargs: Any) -> None:
        print(*args, file=sys.stderr, **kwargs)

    def close(self) -> None:
        self.xml.endElement("logfile")
        self.xml.endDocument()
        self.logfile_handle.close()

    def sanitise(self, message: str) -> str:
        return "".join(ch for ch in message if unicodedata.category(ch)[0] != "C")

    def maybe_prefix(self, message: str, attributes: Dict[str, str]) -> str:
        if "machine" in attributes:
            return f"{attributes['machine']}: {message}"
        return message

    def log_line(self, message: str, attributes: Dict[str, str]) -> None:
        self.xml.startElement("line", attrs=AttributesImpl(attributes))
        self.xml.characters(message)
        self.xml.endElement("line")

    def info(self, *args, **kwargs) -> None:  # type: ignore
        self.log(*args, **kwargs)

    def warning(self, *args, **kwargs) -> None:  # type: ignore
        self.log(*args, **kwargs)

    def error(self, *args, **kwargs) -> None:  # type: ignore
        self.log(*args, **kwargs)
        sys.exit(1)

    def log(self, message: str, attributes: Dict[str, str] = {}) -> None:
        self._eprint(self.maybe_prefix(message, attributes))
        self.drain_log_queue()
        self.log_line(message, attributes)

    def log_serial(self, message: str, machine: str) -> None:
        self.enqueue({"msg": message, "machine": machine, "type": "serial"})
        if self._print_serial_logs:
            self._eprint(Style.DIM + f"{machine} # {message}" + Style.RESET_ALL)

    def enqueue(self, item: Dict[str, str]) -> None:
        self.queue.put(item)

    def drain_log_queue(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                msg = self.sanitise(item["msg"])
                del item["msg"]
                self.log_line(msg, item)
        except Empty:
            pass

    def subtest(self, name: str, attributes: Dict[str, str] = {}) -> Iterator[None]:
        return self.nested("subtest: " + name, attributes)

    def nested(self, message: str, attributes: Dict[str, str] = {}) -> Iterator[None]:
        self._eprint(
            self.maybe_prefix(
                Style.BRIGHT + Fore.GREEN + message + Style.RESET_ALL, attributes
            )
        )

        self.xml.startElement("nest", attrs=AttributesImpl({}))
        self.xml.startElement("head", attrs=AttributesImpl(attributes))
        self.xml.characters(message)
        self.xml.endElement("head")

        tic = time.time()
        self.drain_log_queue()
        yield
        self.drain_log_queue()
        toc = time.time()
        self.log(f"(finished: {message}, in {toc - tic:.2f} seconds)")

        self.xml.endElement("nest")


class JunitXMLLogger:
    def __init__(self) -> None:
        pass

    def info(self, *args, **kwargs) -> None:  # type: ignore
        pass

    def warning(self, *args, **kwargs) -> None:  # type: ignore
        pass

    def error(self, *args, **kwargs) -> None:  # type: ignore
        pass

    def nested(self, message: str, attributes: Dict[str, str] = {}) -> Iterator[None]:
        yield

    def subtest(self, name: str, attributes: Dict[str, str] = {}) -> Iterator[None]:
        yield

    def log(self, message: str, attributes: Dict[str, str] = {}) -> None:
        pass

    def log_serial(self, message: str, machine: str) -> None:
        pass


rootlog: BaseLogger = BaseLogger()
