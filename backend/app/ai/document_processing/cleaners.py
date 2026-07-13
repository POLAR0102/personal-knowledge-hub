import re
import unicodedata

from app.ai.document_processing.parser_result import ParsedDocument, ParsedSection

WHITESPACE_RE = re.compile(r"[ \t]+")


def _remove_control_characters(text: str) -> str:
    return "".join(
        character
        for character in text
        if character in {"\n", "\t"}
        or unicodedata.category(character) not in {"Cc", "Cf"}
    )


def clean_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _remove_control_characters(normalized)
    cleaned_lines: list[str] = []
    in_code_block = False
    blank_line_count = 0

    for line in normalized.split("\n"):
        stripped = line.strip()
        is_fence = stripped.startswith("```") or stripped.startswith("~~~")
        if is_fence:
            cleaned_lines.append(stripped)
            in_code_block = not in_code_block
            blank_line_count = 0
            continue

        if in_code_block:
            cleaned_lines.append(line.rstrip())
            continue

        cleaned_line = WHITESPACE_RE.sub(" ", line).strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
            blank_line_count = 0
        elif cleaned_lines and blank_line_count < 2:
            cleaned_lines.append("")
            blank_line_count += 1

    return "\n".join(cleaned_lines).strip()


def clean_parsed_document(document: ParsedDocument) -> ParsedDocument:
    sections: list[ParsedSection] = []
    for section in document.sections:
        content = clean_text(section.content)
        if not content:
            continue
        title = clean_text(section.section_title) if section.section_title else None
        sections.append(
            ParsedSection(
                content=content,
                section_index=len(sections),
                page_number=section.page_number,
                section_title=title or None,
            )
        )

    return ParsedDocument(sections=sections, metadata=document.metadata.copy())
