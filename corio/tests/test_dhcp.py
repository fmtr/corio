from unittest.mock import AsyncMock, Mock, patch

import pytest

from corio.dhcp.dhcp import Lease

LEASES = "1700000000 AA:BB:CC:DD:EE:FF 10.0.0.2 app--room client-id\n"


def test_lease_parsing_and_indexes():
    leases = Lease.from_leases(LEASES)
    assert leases.mac["aa:bb:cc:dd:ee:ff"].ip == "10.0.0.2"


@pytest.mark.asyncio
async def test_lease_from_url():
    response = Mock(text=LEASES)
    client = AsyncMock()
    client.get.return_value = response

    with patch("corio.dhcp.dhcp.https.AsyncClient") as client_cls:
        client_cls.return_value.__aenter__ = AsyncMock(return_value=client)
        client_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        leases = await Lease.from_url("http://router/leases")

    client.get.assert_awaited_once_with("http://router/leases")
    response.raise_for_status.assert_called_once_with()
    assert leases[0].hostname == "app--room"
