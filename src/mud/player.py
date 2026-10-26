from dataclasses import dataclass, field
from typing import Protocol


class Connection(Protocol):
    def send(self, text: str) -> None: ...

    def clear(self) -> None: ...

    def close(self, farewell: str) -> None: ...


@dataclass(slots=True, kw_only=True)
class Player:
    name: str
    connection: Connection
    room: str
    items: list[str] = field(default_factory=list[str])
