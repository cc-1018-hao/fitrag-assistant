from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from langchain_core.documents import Document


SUPPORTED_EXTENSIONS = {".txt", ".md", ".json"}


def _load_text_file(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    return Document(page_content=text, metadata={"source": str(path), "file_type": path.suffix})


def _load_json_file(path: Path) -> List[Document]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    docs: List[Document] = []

    if isinstance(payload, dict):
        payload = [payload]

    if not isinstance(payload, list):
        raise ValueError(f"Unsupported JSON format in {path}")

    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        metadata = {
            "source": str(path),
            "file_type": path.suffix,
            "record_index": idx,
            "title": item.get("title", ""),
            "section": item.get("section", ""),
            "publish_date": item.get("publish_date", ""),
            "url": item.get("url", ""),
        }
        docs.append(Document(page_content=content, metadata=metadata))
    return docs


def load_documents(data_dir: str) -> List[Document]:
    root = Path(data_dir)
    if not root.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    documents: List[Document] = []
    for file_path in files:
        suffix = file_path.suffix.lower()
        if suffix in {".txt", ".md"}:
            documents.append(_load_text_file(file_path))
        elif suffix == ".json":
            documents.extend(_load_json_file(file_path))
    return documents


def iter_supported_files(data_dir: str) -> Iterable[Path]:
    root = Path(data_dir)
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path
