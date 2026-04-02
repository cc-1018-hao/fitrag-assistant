import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str
    embedding_model: str
    chat_model: str
    chroma_persist_dir: str
    chroma_collection: str
    bm25_corpus_path: str
    chunk_size: int
    chunk_overlap: int
    trust_env_proxy: bool


def get_settings(require_api_key: bool = True) -> Settings:
    openai_api_key = (
        os.getenv("OPENAI_API_KEY", "").strip()
        or os.getenv("QWEN_API_KEY", "").strip()
        or os.getenv("DASHSCOPE_API_KEY", "").strip()
    )
    if require_api_key and not openai_api_key:
        raise ValueError("OPENAI_API_KEY (or QWEN_API_KEY / DASHSCOPE_API_KEY) is required")

    openai_base_url = (
        os.getenv("OPENAI_BASE_URL", "").strip()
        or os.getenv("QWEN_BASE_URL", "").strip()
        or os.getenv("DASHSCOPE_BASE_URL", "").strip()
        or "https://api.openai.com/v1"
    )

    embedding_model = (
        os.getenv("EMBEDDING_MODEL", "").strip()
        or os.getenv("QWEN_EMBEDDING_MODEL", "").strip()
        or "Qwen/Qwen3-Embedding-8B"
    )
    chat_model = (
        os.getenv("CHAT_MODEL", "").strip()
        or os.getenv("QWEN_CHAT_MODEL", "").strip()
        or "gpt-4o"
    )

    return Settings(
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        embedding_model=embedding_model,
        chat_model=chat_model,
        chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./storage/chroma").strip(),
        chroma_collection=os.getenv("CHROMA_COLLECTION", "fitness_knowledge").strip(),
        bm25_corpus_path=os.getenv("BM25_CORPUS_PATH", "./storage/bm25_corpus.jsonl").strip(),
        chunk_size=int(os.getenv("CHUNK_SIZE", "800")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "120")),
        trust_env_proxy=os.getenv("TRUST_ENV_PROXY", "false").strip().lower() in {"1", "true", "yes"},
    )
