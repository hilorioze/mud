import functools
import logging
from typing import cast

import telnetlib3
from telnetlib3 import TelnetReader, TelnetReaderUnicode, TelnetWriter, TelnetWriterUnicode
from telnetlib3.telopt import CHARSET, DO, NAWS
from wcwidth import strip_sequences, wrap

from mud.commands import handle
from mud.game import Game
from mud.player import Player
from mud.world import load_world

logger = logging.getLogger(__name__)


class GameServer(telnetlib3.TelnetServer):
    # greet before negotiation, which a client without telnet, such as nc, makes the server wait out
    def begin_negotiation(self) -> None:
        writer: TelnetWriterUnicode = cast(TelnetWriterUnicode, self.writer)
        writer.write("Welcome!\r\n")

        super().begin_negotiation()

    # `TelnetServer`'s negotiation without `WILL BINARY`, which makes telnet turn off output processing, so its local echo of enter leaves the cursor at the end of the typed line
    def begin_advanced_negotiation(self) -> None:
        writer: TelnetWriterUnicode = cast(TelnetWriterUnicode, self.writer)
        writer.iac(DO, NAWS)
        writer.iac(DO, CHARSET)


class TelnetConnection:
    def __init__(self, writer: TelnetWriterUnicode) -> None:
        self._writer: TelnetWriterUnicode = writer
        self.prompted: bool = False

    def send(self, text: str) -> None:
        self._write(text)

        # a message from another player gives the prompt back
        if self.prompted:
            self.prompt()

    def prompt(self) -> None:
        self._writer.write("> ")
        self._writer.send_ga()
        self.prompted = True

    def clear(self) -> None:
        # move the cursor home and erase the screen
        self._writer.write("\x1b[H\x1b[2J")

    def close(self, farewell: str) -> None:
        self._write(farewell)
        self._writer.close()

    def _write(self, text: str) -> None:
        # start a message from another player on a new line after the prompt
        if self.prompted:
            self._writer.write("\r\n")

        width: int = self._writer.get_extra_info("cols")
        lines: list[str] = []
        for paragraph in text.split("\n"):
            lines.extend(wrap(paragraph, width) or [""])

        self._writer.write("\r\n".join(lines) + "\r\n")


def clean_line(line: str) -> str:
    # keep players from sending terminal escapes and control characters to each other
    return "".join(char for char in strip_sequences(line) if char.isprintable()).strip()


async def read_line(reader: TelnetReaderUnicode, connection: TelnetConnection) -> str | None:
    connection.prompt()

    try:
        line: str = await reader.readline()
    except ConnectionError:
        return None

    connection.prompted = False

    # an empty read is end of file, an empty line still has its line ending
    if not line:
        return None

    return clean_line(line)


async def play(
    game: Game,
    reader: TelnetReader | TelnetReaderUnicode,
    writer: TelnetWriter | TelnetWriterUnicode,
) -> None:
    # `encoding` in `create_server` makes telnetlib3 pass the unicode reader and writer
    lines: TelnetReaderUnicode = cast(TelnetReaderUnicode, reader)
    connection: TelnetConnection = TelnetConnection(cast(TelnetWriterUnicode, writer))

    connection.send("What's your name?")

    player: Player | None = None
    while player is None:
        name: str | None = await read_line(lines, connection)
        if name is None:
            return

        player = game.join(name, connection)

    logger.info("%s joined", player.name)

    try:
        while True:
            line: str | None = await read_line(lines, connection)
            if line is None:
                break

            handle(game, player, line)
    finally:
        game.leave(player)
        logger.info("%s left", player.name)


async def start_server(game: Game, *, host: str, port: int) -> telnetlib3.Server:
    return await telnetlib3.create_server(
        host=host,
        port=port,
        protocol_factory=GameServer,
        shell=functools.partial(play, game),
        encoding="utf8",
        # turn broken utf-8 from a client into `U+FFFD`
        encoding_errors="replace",
        # use utf-8 without binary mode, which `GameServer` doesn't offer
        force_binary=True,
        # mud clients edit the line locally, so don't take over echo
        line_mode=True,
    )


async def serve(*, host: str, port: int) -> None:
    server: telnetlib3.Server = await start_server(Game(load_world()), host=host, port=port)
    logger.info("listening on %s:%d", host, port)

    await server.wait_closed()
