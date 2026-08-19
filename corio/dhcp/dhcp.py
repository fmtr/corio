from dataclasses import dataclass

from corio import https
from corio.iterator import IndexList


@dataclass(frozen=True)
class Lease:
    expiry: int
    mac: str
    ip: str
    hostname: str
    client_id: str | None = None

    @classmethod
    def from_text(cls, text: str) -> "Lease":
        expiry, mac, ip, hostname, *client_id = text.split()
        return cls(
            expiry=int(expiry),
            mac=mac.lower(),
            ip=ip,
            hostname=hostname,
            client_id=client_id[0] if client_id else None,
        )

    @classmethod
    def from_leases(cls, text: str) -> IndexList["Lease"]:
        return IndexList(cls.from_text(line) for line in text.splitlines() if line.strip())

    @classmethod
    async def from_url(cls, url: str) -> IndexList["Lease"]:
        async with https.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
        return cls.from_leases(response.text)
