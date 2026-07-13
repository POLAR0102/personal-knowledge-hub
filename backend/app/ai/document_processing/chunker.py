import hashlib
import re
from dataclasses import dataclass

from app.ai.document_processing.parser_result import ParsedDocument, ParsedSection

PARAGRAPH_BOUNDARY_RE = re.compile(r"\n\s*\n")
SENTENCE_BOUNDARY_RE = re.compile(r"[。！？!?；;.]([\"'”’）)】\]]*)\s*")


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    chunk_index: int
    content: str
    content_hash: str
    character_count: int
    page_number: int | None
    section_title: str | None
    start_offset: int | None
    end_offset: int | None


class Chunker:
    def __init__(
        self,
        *,
        chunk_size: int = 600,
        chunk_overlap: int = 80,
        minimum_chunk_size: int = 40,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be between zero and chunk_size")
        if minimum_chunk_size <= 0 or minimum_chunk_size > chunk_size:
            raise ValueError("minimum_chunk_size must be between one and chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.minimum_chunk_size = minimum_chunk_size

    def split(self, document: ParsedDocument) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for section in document.sections:
            for content, start_offset, end_offset in self._split_section(section):
                drafts.append(
                    ChunkDraft(
                        chunk_index=len(drafts),
                        content=content,
                        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        character_count=len(content),
                        page_number=section.page_number,
                        section_title=section.section_title,
                        start_offset=start_offset,
                        end_offset=end_offset,
                    )
                )
        return drafts

    def _split_section(self, section: ParsedSection) -> list[tuple[str, int, int]]:
        content = section.content.strip()
        if not content:
            return []
        if len(content) <= self.chunk_size:
            return [(content, 0, len(content))]

        pieces: list[tuple[str, int, int]] = []
        start = 0
        content_length = len(content)
        while start < content_length:
            target_end = min(start + self.chunk_size, content_length)
            if target_end == content_length:
                end = content_length
            else:
                end = self._preferred_end(content, start, target_end)
                remaining = content_length - end
                if 0 < remaining < self.minimum_chunk_size:
                    end = max(start + self.minimum_chunk_size, content_length - self.minimum_chunk_size)

            raw_piece = content[start:end]
            left_trim = len(raw_piece) - len(raw_piece.lstrip())
            right_trim = len(raw_piece) - len(raw_piece.rstrip())
            actual_start = start + left_trim
            actual_end = end - right_trim
            piece = content[actual_start:actual_end]
            if piece:
                pieces.append((piece, actual_start, actual_end))
            if end >= content_length:
                break

            next_start = max(end - self.chunk_overlap, start + 1)
            while next_start < content_length and content[next_start].isspace():
                next_start += 1
            start = next_start

        return pieces

    def _preferred_end(self, content: str, start: int, target_end: int) -> int:
        window = content[start:target_end]
        minimum_end = min(self.minimum_chunk_size, len(window))
        paragraph_ends = [match.end() for match in PARAGRAPH_BOUNDARY_RE.finditer(window)]
        valid_paragraph_ends = [end for end in paragraph_ends if end >= minimum_end]
        if valid_paragraph_ends:
            return start + valid_paragraph_ends[-1]

        sentence_ends = [match.end() for match in SENTENCE_BOUNDARY_RE.finditer(window)]
        valid_sentence_ends = [end for end in sentence_ends if end >= minimum_end]
        if valid_sentence_ends:
            return start + valid_sentence_ends[-1]
        return target_end
