import argparse
import asyncio
import contextlib
import logging

from mud.server import serve


def parse_arguments() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="mud",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--host",
        default="localhost",
        help="address to listen on",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=4000,
        help="port to listen on",
    )

    return parser.parse_args()


def main() -> None:
    arguments: argparse.Namespace = parse_arguments()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(serve(host=arguments.host, port=arguments.port))


if __name__ == "__main__":
    main()
