from __future__ import annotations

import pytest


def start_server_or_skip(server) -> None:
    try:
        server.start()
    except PermissionError:
        pytest.skip("Local sandbox does not allow binding a loopback port.")
