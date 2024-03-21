# mypy: disable-error-code="no-untyped-call"
# drop the above line when mypy is upgraded to include
# https://github.com/python/typeshed/commit/49b717ca52bf0781a538b04c0d76a5513f7119b8
import codecs
import os
import sys
import time
import unicodedata
from contextlib import contextmanager
from queue import Empty, Queue
from typing import Any, Dict, Iterator
from xml.sax.saxutils import XMLGenerator

from colorama import Fore, Style
from junit_xml import TestCase, TestSuite


class Logger:
    def __init__(self) -> None:
        self.logfile = os.environ.get("LOGFILE", "/dev/null")
        self.logfile_handle = codecs.open(self.logfile, "wb")
        self.xml = XMLGenerator(self.logfile_handle, encoding="utf-8")
        self.queue: "Queue[Dict[str, str]]" = Queue()

        self.xml.startDocument()
        self.xml.startElement("logfile", attrs={})

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
        self.xml.startElement("line", attributes)
        self.xml.characters(message)
        self.xml.endElement("line")

    def info(self, *args, **kwargs) -> None:  # type: ignore
        self.log(*args, **kwargs)

    def warning(self, *args, **kwargs) -> None:  # type: ignore
        self.log(*args, **kwargs)

    def error(self, *args, **kwargs) -> None:  # type: ignore
        self.log(*args, **kwargs)
        testlog.error(args[0] + "\n")
        sys.exit(1)

    def log(self, message: str, attributes: Dict[str, str] = {}) -> None:
        testlog.log(message + "\n")
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

    @contextmanager
    def nested(self, message: str, attributes: Dict[str, str] = {}) -> Iterator[None]:
        self._eprint(
            self.maybe_prefix(
                Style.BRIGHT + Fore.GREEN + message + Style.RESET_ALL, attributes
            )
        )

        self.xml.startElement("nest", attrs={})
        self.xml.startElement("head", attributes)
        self.xml.characters(message)
        self.xml.endElement("head")

        tic = time.time()
        self.drain_log_queue()
        yield
        self.drain_log_queue()
        toc = time.time()
        self.log(f"(finished: {message}, in {toc - tic:.2f} seconds)")

        self.xml.endElement("nest")


rootlog = Logger()


class TestCaseState:
    def __init__(self) -> None:
        self.stdout = ""
        self.stderr = ""
        self.failure = False
        self.skipped = False
        self.time = float(0)


class TestLog:
    def __init__(self) -> None:
        self.tests: dict[str, TestCaseState] = {"main": TestCaseState()}
        self.currentSubtest: str = "main"
        self.logfile = os.environ.get("LOGFILE_JUNIT", "/dev/null")

    def close(self) -> None:
        with open(self.logfile, "w") as f:
            test_cases = []
            for name, test_case_state in self.tests.items():
                tc = TestCase(
                    name,
                    stdout=test_case_state.stdout,
                    stderr=test_case_state.stderr,
                )
                if test_case_state.failure:
                    tc.add_failure_info("Test Case failed")

                test_cases.append(tc)
            ts = TestSuite("my test suite", test_cases)
            f.write(TestSuite.to_xml_string([ts]))

    @contextmanager
    def subtest(self, name: str) -> Iterator[None]:
        self.currentSubtest = name
        self.tests[name] = TestCaseState()
        tic = time.time()
        yield
        toc = time.time()
        self.tests[name].time = toc - tic
        self.currentSubtest = "main"

    def log(self, line: str) -> None:
        self.tests[self.currentSubtest].stdout += line

    def error(self, line: str) -> None:
        self.tests[self.currentSubtest].stderr += line
        self.tests[self.currentSubtest].failure = True


testlog = TestLog()
