from __future__ import annotations

from dataclasses import dataclass, field
from io import StringIO
from types import CodeType
from typing import Any, Dict, List, Mapping, NoReturn, Optional, Tuple, Type, Union

COLON = ":"


@dataclass
class Code:
    lines: List[Tuple[int, Union[str, Code]]] = field(default_factory=list)
    depth: int = 0
    indent: int = 4
    locals: Dict[str, Any] = field(default_factory=dict)
    globals: Dict[str, Any] = field(default_factory=dict)

    def start_block(self) -> None:
        self.depth += 1

    def end_block(self) -> None:
        self.depth -= 1

    def build_globals(self, **kwargs: Dict[str, Any]) -> dict:
        _globals: dict = self.globals.copy()
        for _, line in self.lines:
            if isinstance(line, Code):
                _globals.update(line.build_globals())
        _globals.update(kwargs)
        return _globals

    def build_locals(self, **kwargs: Dict[str, Any]) -> dict:
        _locals: dict = self.locals.copy()
        for _, line in self.lines:
            if isinstance(line, Code):
                _locals.update(line.build_locals())
        _locals.update(kwargs)
        return _locals

    outdent = end_block

    def full_outdent(self) -> None:
        self.depth = 0

    close = full_outdent

    def add_locals(self, *args: Type[object], **kwargs: Any) -> None:
        for arg in args:
            self.locals[arg.__name__] = arg
        for name, val in kwargs.items():
            self.locals[name] = val

    def add_globals(self, *args: Type[object], **kwargs: Any) -> None:
        for arg in args:
            self.globals[arg.__name__] = arg
        for name, val in kwargs.items():
            self.globals[name] = val

    def add(self, *lines: Union[str, Code]) -> None:
        for line in lines:
            self.lines.append((self.depth, line))
            if isinstance(line, str) and line[-1] == COLON:
                self.start_block()

    def to_string(self, depth: int = 0) -> str:
        stringio = StringIO()
        for line_depth, line in self.lines:
            if isinstance(line, Code):
                stringio.writelines((line.to_string(depth + line_depth)))
            else:
                stringio.writelines(
                    (" " * ((depth + line_depth) * self.indent), line, "\n")
                )

        return stringio.getvalue()

    def compile(self, filename: Optional[str] = None) -> CodeType:
        if filename:
            with open(filename, "w") as f:
                f.write(self.to_string())
        else:
            filename = "<string>"
        return compile(self.to_string(), filename, "exec")

    def exec(
        self,
        filename: Optional[str] = None,
        add_globals: Optional[Dict[str, Any]] = None,
        add_locals: Optional[Mapping[str, Any]] = None,
    ) -> None:
        _globals = self.build_globals(**add_globals or {})
        _locals = self.build_locals(**add_locals or {})
        exec(self.compile(filename), _globals, _locals)  # pylint: disable=W0122
