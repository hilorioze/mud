from dataclasses import dataclass, field

import pytest

from mud.commands import handle
from mud.game import Game
from mud.player import Player
from mud.world import load_world


@dataclass(slots=True)
class FakeConnection:
    messages: list[str] = field(default_factory=list[str])
    cleared: bool = False
    closed: bool = False

    def send(self, text: str) -> None:
        self.messages.append(text)

    def clear(self) -> None:
        self.cleared = True

    def close(self, farewell: str) -> None:
        self.messages.append(farewell)
        self.closed = True

    def last(self) -> str:
        return self.messages[-1]


@pytest.fixture
def game() -> Game:
    return Game(load_world())


def join(game: Game, name: str) -> tuple[Player, FakeConnection]:
    connection: FakeConnection = FakeConnection()
    player: Player | None = game.join(name, connection)
    assert player is not None

    return player, connection


def run(game: Game, player: Player, *lines: str) -> None:
    for line in lines:
        handle(game, player, line)


def test_join_shows_intro_and_starting_room(game: Game) -> None:
    _, connection = join(game, "Ann")

    assert "Gull Rock" in connection.messages[0]
    assert connection.last().startswith("Boat Landing")


@pytest.mark.parametrize("name", ["A", "Abcdefghijklmnopq", "Ann1", "Ann Lee", ""])
def test_join_rejects_bad_names(game: Game, name: str) -> None:
    connection: FakeConnection = FakeConnection()

    assert game.join(name, connection) is None
    assert "letters" in connection.last()


def test_join_rejects_taken_name_in_any_case(game: Game) -> None:
    join(game, "Ann")
    connection: FakeConnection = FakeConnection()

    assert game.join("ANN", connection) is None
    assert "already playing" in connection.last()


def test_join_accepts_non_ascii_name(game: Game) -> None:
    player, _ = join(game, "Їжак")

    assert game.players["їжак"] is player


def test_players_see_each_other_arrive_and_leave(game: Game) -> None:
    ann, ann_connection = join(game, "Ann")
    _, bob_connection = join(game, "Bob")

    assert ann_connection.last() == "Bob arrives."
    assert "Ann is here." in bob_connection.last()

    run(game, ann, "north")

    assert bob_connection.last() == "Ann goes north."


def test_say_reaches_only_the_room_and_shout_reaches_everyone(game: Game) -> None:
    ann, ann_connection = join(game, "Ann")
    _, bob_connection = join(game, "Bob")
    cat, cat_connection = join(game, "Cat")
    run(game, cat, "east")

    run(game, ann, "say привіт")

    assert ann_connection.last() == 'You say, "привіт"'
    assert bob_connection.last() == 'Ann says, "привіт"'
    assert "привіт" not in cat_connection.last()

    run(game, ann, "shout hello")

    assert cat_connection.last() == 'Ann shouts, "hello"'


def test_apostrophe_says_the_rest(game: Game) -> None:
    ann, _ = join(game, "Ann")
    _, bob_connection = join(game, "Bob")

    run(game, ann, "'hi there")

    assert bob_connection.last() == 'Ann says, "hi there"'


def test_tell_reaches_one_player_anywhere(game: Game) -> None:
    ann, ann_connection = join(game, "Ann")
    bob, bob_connection = join(game, "Bob")
    _, cat_connection = join(game, "Cat")
    run(game, bob, "east")
    received: int = len(cat_connection.messages)

    run(game, ann, "tell BOB the key is on the ledge")

    assert ann_connection.last() == 'You tell Bob, "the key is on the ledge"'
    assert bob_connection.last() == 'Ann tells you, "the key is on the ledge"'
    assert len(cat_connection.messages) == received

    run(game, ann, "tell nobody hello")
    assert ann_connection.last() == "Nobody by that name is playing."

    run(game, ann, "tell bob")
    assert ann_connection.last() == "Tell whom what?"


def test_movement_follows_exits(game: Game) -> None:
    ann, connection = join(game, "Ann")

    run(game, ann, "west")
    assert connection.last() == "You can't go that way."

    run(game, ann, "go east")
    assert connection.last().startswith("Boathouse")

    run(game, ann, "w")
    assert ann.room == "landing"


def test_locked_door_opens_with_the_key_for_everyone(game: Game) -> None:
    ann, ann_connection = join(game, "Ann")
    bob, _ = join(game, "Bob")
    run(game, ann, "n", "n", "n")

    assert ann.room == "yard"
    assert "locked" in ann_connection.last()

    run(game, ann, "s", "e", "take key", "w", "n", "n")

    assert ann.room == "tower"
    assert any("screech" in message for message in ann_connection.messages)

    run(game, bob, "n", "n", "n")

    assert bob.room == "tower"


def test_take_drop_and_give_move_items(game: Game) -> None:
    ann, ann_connection = join(game, "Ann")
    bob, bob_connection = join(game, "Bob")
    run(game, ann, "e", "take the can")

    assert ann.items == ["oil"]
    assert game.room_items["boathouse"] == []

    run(game, ann, "drop oil")

    assert game.room_items["boathouse"] == ["oil"]

    run(game, ann, "get oil", "w", "give oil to bob")

    assert bob.items == ["oil"]
    assert ann_connection.last() == "You give a can of lamp oil to Bob."
    assert bob_connection.last() == "Ann gives you a can of lamp oil."


def test_fixed_items_stay_put(game: Game) -> None:
    ann, connection = join(game, "Ann")
    ann.room = "lantern"

    run(game, ann, "take lamp")

    assert connection.last() == "The lamp is bolted into the lens. It is not going anywhere."
    assert "lamp" in game.room_items["lantern"]


def test_look_shows_items_and_players(game: Game) -> None:
    ann, connection = join(game, "Ann")
    bob, _ = join(game, "Bob")
    run(game, bob, "e", "take oil", "w")

    run(game, ann, "look at bob")
    assert connection.last() == "Bob is carrying a can of lamp oil."

    run(game, ann, "look oil")
    assert connection.last() == "You don't see that here."

    run(game, ann, "e", "look")
    assert "You see" not in connection.last()


def test_leaving_drops_carried_items(game: Game) -> None:
    ann, _ = join(game, "Ann")
    _, bob_connection = join(game, "Bob")
    run(game, ann, "e", "take oil", "w")

    game.leave(ann)

    assert "ann" not in game.players
    assert game.room_items["landing"] == ["oil"]
    assert bob_connection.last() == "Ann has left the game."


def test_goal_needs_the_room_and_the_items(game: Game) -> None:
    ann, connection = join(game, "Ann")

    run(game, ann, "light")
    assert connection.last() == "You can't do that here."

    ann.room = "lantern"
    run(game, ann, "light lamp")
    assert connection.last() == game.world.goal.missing


def test_lighting_the_lamp_ends_the_round_for_everyone(game: Game) -> None:
    ann, ann_connection = join(game, "Ann")
    bob, bob_connection = join(game, "Bob")
    ann.items = ["oil", "matches"]
    ann.room = "lantern"
    game.room_items["boathouse"].clear()

    run(game, ann, "light")

    assert f"Ann {game.world.goal.done}" in ann_connection.messages
    assert f"Ann {game.world.goal.done}" in bob_connection.messages
    assert ann_connection.last() == bob_connection.last() == game.world.goal.ending
    assert ann_connection.closed
    assert bob_connection.closed
    assert game.players == {}
    assert game.room_items["boathouse"] == ["oil"]

    game.leave(bob)
    join(game, "Ann")

    assert list(game.players) == ["ann"]


def test_unknown_and_empty_input(game: Game) -> None:
    ann, connection = join(game, "Ann")
    received: int = len(connection.messages)

    run(game, ann, "   ")
    assert len(connection.messages) == received

    run(game, ann, "dance")
    assert connection.last().startswith("I don't understand that.")


@pytest.mark.parametrize(
    ("line", "reply"),
    [
        ("go", "Go where?"),
        ("take", "Take what?"),
        ("drop", "Drop what?"),
        ("give key", "Give what to whom?"),
        ("'", "Say what?"),
    ],
)
def test_commands_without_arguments_ask_for_them(game: Game, line: str, reply: str) -> None:
    ann, connection = join(game, "Ann")

    run(game, ann, line)

    assert connection.last() == reply


@pytest.mark.parametrize("command", ["clear", "cls"])
def test_clear_clears_the_screen(game: Game, command: str) -> None:
    ann, connection = join(game, "Ann")

    run(game, ann, command)

    assert connection.cleared


@pytest.mark.parametrize("command", ["quit", "q", "exit"])
def test_quit_closes_the_connection(game: Game, command: str) -> None:
    ann, connection = join(game, "Ann")

    run(game, ann, command)

    assert connection.last() == "Goodbye."
    assert connection.closed
