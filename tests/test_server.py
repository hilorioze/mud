import asyncio
from collections.abc import AsyncIterator

import pytest
import telnetlib3
from telnetlib3.telopt import GA, IAC, TTYPE, WILL, WONT

from mud.game import Game
from mud.server import start_server
from mud.world import load_world

PROMPT: bytes = b"> " + IAC + GA


@pytest.fixture
async def port() -> AsyncIterator[int]:
    server: telnetlib3.Server = await start_server(Game(load_world()), host="127.0.0.1", port=0)
    assert server.sockets is not None

    yield server.sockets[0].getsockname()[1]

    server.close()
    await server.wait_closed()


async def read_prompt(reader: asyncio.StreamReader) -> str:
    data: bytes = await asyncio.wait_for(reader.readuntil(PROMPT), timeout=5)

    return data.decode(errors="replace")


async def connect(port: int, name: str) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    # answering the terminal type question ends negotiation without the server's wait
    writer.write(IAC + WONT + TTYPE)
    await read_prompt(reader)

    writer.write(f"{name}\r\n".encode())
    await read_prompt(reader)

    return reader, writer


async def test_two_players_talk_in_unicode(port: int) -> None:
    ann_reader, ann_writer = await connect(port, "Ann")
    bob_reader, bob_writer = await connect(port, "Їжак")

    assert "Їжак arrives." in await read_prompt(ann_reader)

    bob_writer.write("say привіт, 日本語\r\n".encode())

    assert 'You say, "привіт, 日本語"' in await read_prompt(bob_reader)
    assert 'Їжак says, "привіт, 日本語"' in await read_prompt(ann_reader)

    ann_writer.close()
    bob_writer.close()


async def test_odd_input_is_cleaned_and_the_session_survives(port: int) -> None:
    ann_reader, ann_writer = await connect(port, "Ann")
    bob_reader, bob_writer = await connect(port, "Bob")
    await read_prompt(ann_reader)

    # terminal escapes, a bell, a stray telnet command, broken utf-8 and a cr nul line ending
    bob_writer.write(b"say \x1b[2J\x1b[31mred\x07 " + IAC + WILL + b"\x01 \xc3\x28 end\r\x00")

    assert 'Bob says, "red  �( end"' in await read_prompt(ann_reader)
    assert 'You say, "red  �( end"' in await read_prompt(bob_reader)

    bob_writer.write(b"who\n")

    assert "Ann: Boat Landing" in await read_prompt(bob_reader)

    ann_writer.close()
    bob_writer.close()


async def test_disconnect_removes_the_player(port: int) -> None:
    ann_reader, ann_writer = await connect(port, "Ann")
    _, bob_writer = await connect(port, "Bob")
    await read_prompt(ann_reader)

    bob_writer.transport.abort()

    assert "Bob has left the game." in await read_prompt(ann_reader)

    ann_writer.write(b"quit\r\n")

    assert (await ann_reader.read()).endswith(b"Goodbye.\r\n")
