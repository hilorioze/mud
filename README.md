# Gull Rock

A multiplayer text game played over telnet. The lighthouse on Gull Rock has gone dark before a storm, and the players on the island have to light it again. When someone does, everyone sees the ending and gets disconnected, and the island resets for the next round.

## Playing

```sh
telnet mud.hilorioze.com 4000
```

Tested with `telnet`, `nc` and [TinTin++](https://tintin.mudhalla.net/). Text is UTF-8.

| Command | |
| --- | --- |
| `look [item or player]`, `l`, `examine`, `x` | describe the room, an item or what a player carries |
| `north`, `south`, `east`, `west`, `up`, `down`, `n`, `s`, `e`, `w`, `u`, `d`, `go <direction>` | move |
| `take <item>`, `get <item>` | pick up an item |
| `drop <item>` | put down an item |
| `give <item> to <player>` | give an item to a player in the same room |
| `inventory`, `inv`, `i` | list carried items |
| `say <text>`, `'<text>` | talk to the room |
| `shout <text>` | talk to everyone |
| `tell <player> <text>` | talk to one player anywhere |
| `who` | list players and their rooms |
| `clear`, `cls` | clear the screen (the client has to support the ANSI `ESC[2J` code) |
| `help`, `h`, `?` | list commands |
| `quit`, `q`, `exit` | leave |

## Running

`mud` starts the server on `localhost:4000`; `--host` and `--port` change that.

- with [devenv](https://devenv.sh/): `direnv allow` or `devenv shell`, then `mud`
- with [uv](https://docs.astral.sh/uv/): `uv run mud`
- with Nix: `nix run github:hilorioze/mud`

## Development

`devenv test` runs treefmt (ruff, alejandra, deadnix, statix, keep-sorted), pyright, actionlint, eclint and pytest.

- `src/mud/data/world.toml`: rooms, items and the goal
- `src/mud/world.py`: loads `world.toml` into dataclasses
- `src/mud/player.py`: a player and the connection the game talks to
- `src/mud/game.py`: game state and rules, no networking
- `src/mud/commands.py`: player commands on top of the game
- `src/mud/server.py`: telnet server on [telnetlib3](https://github.com/jquast/telnetlib3)
- `tests/`: game rules, world consistency and telnet sessions

## World format

```toml
[rooms.yard]
name = "Lighthouse Yard"
description = "..."

exits = {north = "tower", south = "path", west = "cottage"}

[rooms.yard.locks.north]
item = "key"

locked = "The lighthouse door is locked."
unlocked = "The iron key turns with a screech, and the lighthouse door swings open."

[items.key]
name = "an iron key"
description = "A big old key, red with rust."
```

- a room has `name`, `description`, `exits` and optional `items` and `locks`; a locked exit opens for everyone once someone with the item goes through it
- an item has `name`, `description` and optional `aliases`, and `fixed` with the message for items that can't be taken
- `[goal]` has the `room`, the `verb` and the `items` needed, and the texts `help` (shown after the verb in the command list), `missing`, `done` (shown to everyone after the player's name) and `ending`

## License

[MIT](LICENSE)
