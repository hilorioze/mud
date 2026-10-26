import tomllib
from dataclasses import dataclass, field
from enum import StrEnum
from importlib.resources import files

from adaptix import ExtraForbid, Retort, name_mapping


class Direction(StrEnum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    UP = "up"
    DOWN = "down"


@dataclass(frozen=True, slots=True, kw_only=True)
class Lock:
    item: str
    locked: str
    unlocked: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Room:
    name: str
    description: str
    exits: dict[Direction, str]
    locks: dict[Direction, Lock] = field(default_factory=dict[Direction, Lock])
    items: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class Item:
    name: str
    description: str
    aliases: tuple[str, ...] = ()
    fixed: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Goal:
    room: str
    verb: str
    items: tuple[str, ...]
    help: str
    missing: str
    done: str
    ending: str


@dataclass(frozen=True, slots=True, kw_only=True)
class World:
    title: str
    intro: str
    start: str
    rooms: dict[str, Room]
    items: dict[str, Item]
    goal: Goal


# reject unknown keys, so a typo in `world.toml` fails the load
_RETORT: Retort = Retort(recipe=[name_mapping(extra_in=ExtraForbid())])


def load_world() -> World:
    text: str = files("mud").joinpath("data", "world.toml").read_text()

    return _RETORT.load(tomllib.loads(text), World)
