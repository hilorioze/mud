from collections.abc import Callable

from mud.game import Game
from mud.player import Player
from mud.world import Direction, Lock

type Command = Callable[[Game, Player, str], None]

COMMANDS: dict[str, Command] = {}

# each direction by its name and by its first letter, `n` for `north`
DIRECTIONS: dict[str, Direction] = {
    name: direction for direction in Direction for name in (direction, direction[0])
}

HELP: list[str] = []


def command(*names: str, description: str) -> Callable[[Command], Command]:
    def register(handler: Command) -> Command:
        for name in names:
            COMMANDS[name] = handler

        HELP.append(f"{', '.join(names)}: {description}")

        return handler

    return register


def handle(game: Game, player: Player, line: str) -> None:
    text: str = line.strip()

    # a leading sign is a command of its own, so `'hello` needs no space
    if text[:1].isalnum():
        first, _, rest = text.partition(" ")
    else:
        first, rest = text[:1], text[1:]

    verb: str = first.casefold()
    args: str = rest.strip()

    if not verb:
        return

    if verb == game.world.goal.verb:
        game.attempt_goal(player)
    elif verb in DIRECTIONS:
        go(game, player, verb)
    elif verb in COMMANDS:
        COMMANDS[verb](game, player, args)
    else:
        player.connection.send("I don't understand that. Type help for a list of commands.")


@command("look", "l", "examine", "x", description="look around, or at something or someone")
def look(game: Game, player: Player, args: str) -> None:
    if not args:
        player.connection.send(game.describe_room(player))

        return

    item: str | None = game.find_item(args, game.room_items[player.room] + player.items)
    if item is not None:
        player.connection.send(game.world.items[item].description)

        return

    other: Player | None = game.find_player(args.rsplit(maxsplit=1)[-1], player.room)
    if other is None:
        player.connection.send("You don't see that here.")
    elif other.items:
        player.connection.send(f"{other.name} is carrying {game.item_names(other.items)}.")
    else:
        player.connection.send(f"{other.name} is empty-handed.")


@command(
    "go",
    description=f"walk {', '.join(Direction)}; the direction alone or its first letter works too",
)
def go(game: Game, player: Player, args: str) -> None:
    if not args:
        player.connection.send("Go where?")

        return

    direction: Direction | None = DIRECTIONS.get(args.casefold())
    room_exits: dict[Direction, str] = game.world.rooms[player.room].exits
    if direction is None or direction not in room_exits:
        player.connection.send("You can't go that way.")

        return

    lock: Lock | None = game.world.rooms[player.room].locks.get(direction)
    if lock is not None and (player.room, direction) not in game.unlocked:
        if lock.item not in player.items:
            player.connection.send(lock.locked)

            return

        game.unlocked.add((player.room, direction))

        player.connection.send(lock.unlocked)

    game.tell_room(player, f"{player.name} goes {direction}.")

    player.room = room_exits[direction]

    game.tell_room(player, f"{player.name} arrives.")
    player.connection.send(game.describe_room(player))


@command("take", "get", description="pick something up")
def take(game: Game, player: Player, args: str) -> None:
    if not args:
        player.connection.send("Take what?")

        return

    item: str | None = game.find_item(args, game.room_items[player.room])
    if item is None:
        player.connection.send("You don't see that here.")

        return

    fixed: str | None = game.world.items[item].fixed
    if fixed is not None:
        player.connection.send(fixed)

        return

    game.room_items[player.room].remove(item)
    player.items.append(item)

    player.connection.send(f"You take {game.world.items[item].name}.")
    game.tell_room(player, f"{player.name} takes {game.world.items[item].name}.")


@command("drop", description="put something down")
def drop(game: Game, player: Player, args: str) -> None:
    if not args:
        player.connection.send("Drop what?")

        return

    item: str | None = game.find_item(args, player.items)
    if item is None:
        player.connection.send("You aren't carrying that.")

        return

    player.items.remove(item)
    game.room_items[player.room].append(item)

    player.connection.send(f"You drop {game.world.items[item].name}.")
    game.tell_room(player, f"{player.name} drops {game.world.items[item].name}.")


@command("give", description="give something to someone")
def give(game: Game, player: Player, args: str) -> None:
    noun, _, name = args.partition(" to ")
    if not noun or not name.strip():
        player.connection.send("Give what to whom?")

        return

    item: str | None = game.find_item(noun, player.items)
    if item is None:
        player.connection.send("You aren't carrying that.")

        return

    other: Player | None = game.find_player(name.strip(), player.room)
    if other is None or other is player:
        player.connection.send("There is nobody here by that name.")

        return

    player.items.remove(item)
    other.items.append(item)

    player.connection.send(f"You give {game.world.items[item].name} to {other.name}.")
    other.connection.send(f"{player.name} gives you {game.world.items[item].name}.")


@command("inventory", "inv", "i", description="list what you are carrying")
def inventory(game: Game, player: Player, _args: str) -> None:
    if player.items:
        player.connection.send(f"You are carrying {game.item_names(player.items)}.")
    else:
        player.connection.send("You are empty-handed.")


@command("say", "'", description="talk to the people in the room")
def say(game: Game, player: Player, args: str) -> None:
    if not args:
        player.connection.send("Say what?")

        return

    player.connection.send(f'You say, "{args}"')
    game.tell_room(player, f'{player.name} says, "{args}"')


@command("shout", description="talk to everyone on the island")
def shout(game: Game, player: Player, args: str) -> None:
    if not args:
        player.connection.send("Shout what?")

        return

    player.connection.send(f'You shout, "{args}"')
    for other in game.players.values():
        if other is not player:
            other.connection.send(f'{player.name} shouts, "{args}"')


@command("tell", description="talk to one player, wherever they are")
def tell(game: Game, player: Player, args: str) -> None:
    name, _, rest = args.partition(" ")
    text: str = rest.strip()
    if not text:
        player.connection.send("Tell whom what?")

        return

    other: Player | None = game.players.get(name.casefold())
    if other is None or other is player:
        player.connection.send("Nobody by that name is playing.")

        return

    player.connection.send(f'You tell {other.name}, "{text}"')
    other.connection.send(f'{player.name} tells you, "{text}"')


@command("who", description="list the players and where they are")
def who(game: Game, player: Player, _args: str) -> None:
    lines: list[str] = [
        f"{other.name}: {game.world.rooms[other.room].name}" for other in game.players.values()
    ]

    player.connection.send("\n".join(["Players on the island:", *lines]))


@command("clear", "cls", description="clear the screen")
def clear(_game: Game, player: Player, _args: str) -> None:
    player.connection.clear()


@command("help", "h", "?", description="show this list")
def show_help(game: Game, player: Player, _args: str) -> None:
    player.connection.send(
        "\n".join(["Commands:", *HELP, f"{game.world.goal.verb}: {game.world.goal.help}"])
    )


@command("quit", "q", "exit", description="leave the game")
def quit_game(_game: Game, player: Player, _args: str) -> None:
    player.connection.close("Goodbye.")
