from collections.abc import Iterable

from mud.player import Connection, Player
from mud.world import Direction, Goal, World


def join_words(words: Iterable[str]) -> str:
    listed: list[str] = list(words)
    if len(listed) == 1:
        return listed[0]

    return f"{', '.join(listed[:-1])} and {listed[-1]}"


class Game:
    def __init__(self, world: World) -> None:
        self.world: World = world
        self._reset()

    def join(self, name: str, connection: Connection) -> Player | None:
        if not 2 <= len(name) <= 16 or not name.isalpha():
            connection.send("Names are 2 to 16 letters, nothing else.")

            return None

        if name.casefold() in self.players:
            connection.send(f"{name} is already playing. Pick another name.")

            return None

        player: Player = Player(name=name, connection=connection, room=self.world.start)
        self.players[name.casefold()] = player

        connection.send(
            f"{self.world.title}\n\n{self.world.intro}\n\nType help for a list of commands.\n"
        )
        self.tell_room(player, f"{name} arrives.")
        connection.send(self.describe_room(player))

        return player

    def leave(self, player: Player) -> None:
        # a finished round has already removed everyone, and someone may have taken the name since
        if self.players.get(player.name.casefold()) is not player:
            return

        del self.players[player.name.casefold()]
        self.room_items[player.room].extend(player.items)

        self.tell_room(player, f"{player.name} has left the game.")

    def players_in(self, room: str) -> list[Player]:
        return [player for player in self.players.values() if player.room == room]

    def tell_room(self, player: Player, text: str) -> None:
        for other in self.players_in(player.room):
            if other is not player:
                other.connection.send(text)

    def find_item(self, noun: str, item_ids: list[str]) -> str | None:
        # the last word names the thing, so `take the iron key` finds `key`
        word: str = noun.rsplit(maxsplit=1)[-1].casefold() if noun else ""

        for item_id in item_ids:
            if word == item_id or word in self.world.items[item_id].aliases:
                return item_id

        return None

    def find_player(self, name: str, room: str) -> Player | None:
        other: Player | None = self.players.get(name.casefold())
        if other is None or other.room != room:
            return None

        return other

    def item_names(self, item_ids: list[str]) -> str:
        return join_words(self.world.items[item_id].name for item_id in item_ids)

    def describe_room(self, player: Player) -> str:
        lines: list[str] = [
            self.world.rooms[player.room].name,
            self.world.rooms[player.room].description,
        ]

        items: list[str] = self.room_items[player.room]
        if items:
            lines.append(f"You see {self.item_names(items)}.")

        others: list[str] = [
            other.name for other in self.players_in(player.room) if other is not player
        ]
        if len(others) == 1:
            lines.append(f"{others[0]} is here.")
        elif others:
            lines.append(f"{join_words(others)} are here.")

        lines.append(f"Exits: {', '.join(self.world.rooms[player.room].exits)}.")

        return "\n".join(lines)

    def attempt_goal(self, player: Player) -> None:
        goal: Goal = self.world.goal
        if player.room != goal.room:
            player.connection.send("You can't do that here.")

            return

        if not all(item in player.items for item in goal.items):
            player.connection.send(goal.missing)

            return

        for other in self.players.values():
            other.connection.send(f"{player.name} {goal.done}")

        for other in self.players.values():
            other.connection.close(goal.ending)

        self._reset()

    def _reset(self) -> None:
        self.players: dict[str, Player] = {}
        self.room_items: dict[str, list[str]] = {
            room_id: list(room.items) for room_id, room in self.world.rooms.items()
        }
        self.unlocked: set[tuple[str, Direction]] = set()
