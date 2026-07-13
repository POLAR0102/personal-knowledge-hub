from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ParsedSection:
    content: str
    section_index: int
    page_number: int | None = None
    section_title: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    sections: list[ParsedSection]
    metadata: dict[str, object] = field(default_factory=dict)
