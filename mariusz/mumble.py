"""Module that provides Mumble-related logic."""

import struct
import socket
import logging

LOGGER = logging.getLogger(__name__)


def get_mumble_user_count(mumble_server: str) -> int:
    """Sends a PING to a given Mumble server and returns the number of
    Mumble users that are currently online. Returns zero on error."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((mumble_server, 64738))
        s.send(b"\x00\x00\x00\x00abcdefgh")
        x = s.recv(1024)
        return int(struct.unpack(">xxxx" + "x" * len("abcdefgh") + "I" * 3, x)[0])
    except socket.error as e:
        LOGGER.error("get_mumble_user_count: %r", e)
        return 0
