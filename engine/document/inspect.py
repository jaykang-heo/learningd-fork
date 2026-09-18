"""lesson.html structural inspection (spec 27, 25.2, 45.4).

The renderer marks semantic elements with data attributes so that gates read
structure instead of guessing from prose:

    data-scene="S08"                 one section per scene, in graph order
    data-visual="dynamic|static|hybrid" substantive visual
    data-visual-role="recap,contrast,proof"
    data-fact="fact.id"              a rendered canonical fact reference
    data-static-fallback="true"      the fallback a dynamic artifact must carry
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

_SCRIPT_SRC = re.compile(r"<script[^>]+src\s*=\s*['\"](?!data:)([^'\"]+)", re.I)
_REMOTE = re.compile(r"^(https?:)?//", re.I)


@dataclass(frozen=True)
class VisualElement:
    kind: str
    roles: tuple[str, ...]
    scene_id: str | None
    has_static_fallback: bool
    interactive: tuple[str, ...]


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scenes: list[str] = []
        self.visuals: list[VisualElement] = []
        self.fact_refs: list[str] = []
        self.text_chars = 0
        self._scene_stack: list[str] = []
        self._pending_fallback: list[bool] = []

    def handle_starttag(self, tag, attrs):
        attributes = {k.lower(): (v or "") for k, v in attrs}
        if "data-scene" in attributes:
            self.scenes.append(attributes["data-scene"])
            self._scene_stack.append(attributes["data-scene"])
        if "data-visual" in attributes:
            self.visuals.append(
                VisualElement(
                    kind=attributes["data-visual"],
                    roles=tuple(r.strip() for r in attributes.get("data-visual-role", "").split(",") if r.strip()),
                    scene_id=self._scene_stack[-1] if self._scene_stack else None,
                    has_static_fallback=attributes.get("data-static-fallback", "") == "true",
                    interactive=tuple(
                        r.strip()
                        for r in attributes.get("data-interactive", "").split(",")
                        if r.strip()
                    ),
                )
            )
        if "data-fact" in attributes:
            self.fact_refs.append(attributes["data-fact"])

    def handle_endtag(self, tag):
        # Scene sections are the only tracked nesting; a close tag of the same
        # depth ends the innermost one conservatively.
        if self._scene_stack and tag in ("section", "article", "div"):
            self._scene_stack.pop()

    def handle_data(self, data):
        self.text_chars += len(data.strip())


@dataclass(frozen=True)
class DocumentReport:
    path: Path
    html: str
    scenes: tuple[str, ...]
    visuals: tuple[VisualElement, ...]
    fact_refs: tuple[str, ...]
    text_chars: int

    def substantive_visuals(self) -> tuple[VisualElement, ...]:
        return tuple(v for v in self.visuals if v.kind in ("static", "dynamic", "hybrid"))

    def dynamic_visuals(self) -> tuple[VisualElement, ...]:
        return tuple(v for v in self.visuals if v.kind in ("dynamic", "hybrid"))

    def with_role(self, role: str) -> tuple[VisualElement, ...]:
        return tuple(v for v in self.substantive_visuals() if role in v.roles)

    def remote_script_sources(self) -> tuple[str, ...]:
        return tuple(src for src in _SCRIPT_SRC.findall(self.html) if _REMOTE.match(src))


def inspect(path: str | Path) -> DocumentReport:
    path = Path(path)
    html = path.read_text(encoding="utf-8")
    collector = _Collector()
    collector.feed(html)
    return DocumentReport(
        path=path,
        html=html,
        scenes=tuple(collector.scenes),
        visuals=tuple(collector.visuals),
        fact_refs=tuple(collector.fact_refs),
        text_chars=collector.text_chars,
    )
