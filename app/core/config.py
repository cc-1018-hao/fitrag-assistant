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
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if require_api_key and not openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")
    return Settings(
        openai_api_key=openai_api_key,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B").strip(),
        chat_model=os.getenv("CHAT_MODEL", "gpt-4o").strip(),
        chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./storage/chroma").strip(),
        chroma_collection=os.getenv("CHROMA_COLLECTION", "fitness_knowledge").strip(),
        bm25_corpus_path=os.getenv("BM25_CORPUS_PATH", "./storage/bm25_corpus.jsonl").strip(),
        chunk_size=int(os.getenv("CHUNK_SIZE", "800")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "120")),
        trust_env_proxy=os.getenv("TRUST_ENV_PROXY", "false").strip().lower() in {"1", "true", "yes"},
    )
