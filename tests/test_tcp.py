import asyncio

from scripts.quick_test import check_tcp_loopback


def test_tcp_loopback() -> None:
    asyncio.run(check_tcp_loopback())
