import logging

from dataclasses import dataclass
from typing import Optional


@dataclass
class PackageVersion:
    line: str
    package_name: str
    package_name_full: str
    package_name_clean: str
    current_version: str
    operand: str
    is_comment: bool
    is_empty: bool
    is_error: Optional[str] = None

    def __init__(self, *args, **kwargs):
        self.line = kwargs.get('line') if 'line' in kwargs else args[0]
        self.ctx =  kwargs.get('ctx') if 'ctx' in kwargs else args[1]
        self.parse_line()

    def extract_op(self, line: str) -> str:
        ops = ["<=", ">=", "==", "!=", "~=", ">", "<"]
        for op in ops:
            if line.find(op) >= 0:
                return op

        return ""

    def parse_line(self):
        try:
            line = self.line.strip()

            # logging.debug(f"parsing line: '{line}'")
            # logging.debug(f"line len: '{len(line)}'")

            self.is_empty = len(line) == 0
            self.is_comment = "#" in line and line.index("#") == 0

            # logging.debug('comment: ', self.is_comment)
            # logging.debug('empty: ', self.is_empty)

            if self.is_empty or self.is_comment:
                # logging.debug('Skipping empty line or comment.')
                return

            op = self.extract_op(line.strip())
            parts = [part.strip() for part in line.split(op)]

            # logging.info("Package Name Parts: ")
            # logging.info(parts)

            self.package_name = parts[0].strip()
            self.package_name_full = parts[0].strip()
            self.package_name_clean = parts[0].strip()
            self.current_version = parts[1] if op else None
            self.operand = op if op else None
        except Exception as err:
            self.is_error = str(err)
            logging.exception(f'Could not parse line: "{line}"', err)

