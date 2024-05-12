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

    def parse_line(self):
        try:
            line = self.line.strip()

            if self.ctx.get("debug"):
                print(f"parsing line: '{line}'")
                print(f"line len: '{len(line)}'")

            self.is_empty = len(line) == 0
            self.is_comment = "#" in line and line.index("#") == 0

            if self.ctx.get("debug"):
                print('comment: ', self.is_comment)
                print('empty: ', self.is_empty)

            if self.is_empty or self.is_comment:
                if self.ctx.get("debug"):
                    print('Skipping empty line or comment.')
                return

            op = self.extract_op(line.strip())
            parts = [part.strip() for part in line.split(op)]
            self.package_name = parts[0]
            self.package_name_full = parts[0]
            self.package_name_clean = parts[0]
            self.current_version = parts[1] if op else None
            self.operand = op if op else None
        except Exception as e:
            self.is_error = str(e)
            print(f'Could not parse line: "{line}"')
            print(e)

    # def to_dict(self) -> dict:
    #     return {
    #         "package_name": self.package_name,
    #         "current_version": self.current_version,
    #         "op": self.operand,
    #     }
