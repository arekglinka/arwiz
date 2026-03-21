from typing import Protocol

from arwiz.foundation import HotSpot


class TemplateOptimizerProtocol(Protocol):
    def apply_template(self, source_code: str, template_name: str) -> str: ...

    def list_templates(self) -> list[str]: ...

    def detect_applicable_templates(
        self,
        source_code: str,
        hotspot: HotSpot | None = None,
    ) -> list[str]: ...
