from dataclasses import dataclass
from typing import Optional

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from indexer.parser import ParsedFile

CHUNK_SIZE = 500  # characters, not lines or tokens
CHUNK_OVERLAP = 50

# Parser language -> LangChain language, which picks code-aware split points
# (e.g. "\nclass ", "\ndef " for Python). SQL has no LangChain preset.
LANGCHAIN_LANGUAGES = {
    "python": Language.PYTHON,
    "javascript": Language.JS,
    "typescript": Language.TS,
    "go": Language.GO,
    "markdown": Language.MARKDOWN,
}


@dataclass
class Chunk:
    file_path: str
    language: str
    content: str
    start_line: int  # 1-based, inclusive, same as the editor
    end_line: int
    chunk_type: str = "block"  # function/class once tree-sitter chunking lands
    chunk_name: Optional[str] = None


def _make_splitter(language: str) -> RecursiveCharacterTextSplitter:
    # add_start_index records where each chunk starts in the file, in characters
    options = dict(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, add_start_index=True)
    if language in LANGCHAIN_LANGUAGES:
        return RecursiveCharacterTextSplitter.from_language(LANGCHAIN_LANGUAGES[language], **options)
    return RecursiveCharacterTextSplitter(**options)


# Built once and reused for every file
SPLITTERS = {language: _make_splitter(language) for language in [*LANGCHAIN_LANGUAGES, "sql"]}


def chunk_data(parsed_file: ParsedFile) -> list[Chunk]:
    """
    Splits one file into overlapping chunks and works out the lines each covers.

    Args:
        parsed_file (ParsedFile): A file returned by parse_github_repo.

    Returns:
        list[Chunk]: The file's chunks in order, with 1-based start/end lines.
    """
    content = parsed_file.content
    splitter = SPLITTERS.get(parsed_file.language) or _make_splitter(parsed_file.language)

    chunks = []
    for doc in splitter.create_documents([content]):
        start_index = doc.metadata["start_index"]
        # Line number = newlines before the chunk + 1; the chunk's own newlines give its length
        start_line = content.count("\n", 0, start_index) + 1
        end_line = start_line + doc.page_content.count("\n")

        chunks.append(
            Chunk(
                file_path=parsed_file.file_path,
                language=parsed_file.language,
                content=doc.page_content,
                start_line=start_line,
                end_line=end_line,
            )
        )

    return chunks


def chunk_files(parsed_files: list[ParsedFile]) -> list[Chunk]:
    """Chunks every parsed file of a repository."""
    return [chunk for parsed_file in parsed_files for chunk in chunk_data(parsed_file)]
