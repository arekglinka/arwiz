from typing import Protocol

from arwiz.foundation import BackendInfo, HotSpot


class BackendSelectorProtocol(Protocol):
    def select_backends(
        self,
        source_code: str,
        hotspot: HotSpot | None = None,
    ) -> list[str]: ...

    def get_manifest(self) -> dict[str, BackendInfo]: ...

    def is_backend_available(self, name: str) -> bool: ...

    def rank_backends(
        self,
        source_code: str,
        hotspot: HotSpot | None = None,
    ) -> list[tuple[str, float]]: ...
