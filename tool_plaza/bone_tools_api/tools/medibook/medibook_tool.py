"""
medical book()
-: build_medibook_index.py generate index, server
"""
import os
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import sys
import numpy as np
from collections import OrderedDict

from FlagEmbedding import FlagAutoModel
from openai import OpenAI

sys.path.append(str(Path(__file__).parent.parent))
from base import Tool, ToolParameter


class MedicalBookTool(Tool):
    def __init__(self, data_dir: str = None):
        super().__init__(
            name="medibook.search",
            description=",,, "
        )

        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "medibook"
        self.data_dir = Path(data_dir)

        self.book = json.load(open(self.data_dir / "medical_books_content.json", "r", encoding="utf-8"))

        # ---- query embedding: modelload(), tokenize ----
        self.embedding_model = FlagAutoModel.from_finetuned(
            "BAAI/bge-base-zh-v1.5",
            query_instruction_for_retrieval="generate: ",
            use_fp16=True,
            devices=["cpu"],
        )

        try:
            self.chat_model = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE"))
        except Exception as e:
            print(f"OpenAI: {e}")
            self.chat_model = None

        # output
        self._DEFAULT_TOP_K = 5
        self._DEFAULT_MAX_CHARS = 2500

        # (generate)
        self.index_dir = Path("tool_plaza/bone_tools_api/tools/medibook/index")
        self.keys_meta = None          # list[dict]
        self.keys_emb = None           # np.ndarray (N, D) float16/float32 (mmap)
        self.leaf_meta = None          # list[dict]
        self.chunks_emb = None         # np.ndarray (M, D) mmap
        self._chunks_text = None       # chunks.jsonl path()

        self._leaf_path_to_id = {}     # path_str -> leaf_id

        self._load_index_if_exists()

        # query embedding LRU(, query encode)
        self._q_cache = OrderedDict()
        self._Q_CACHE_MAX = 256

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="query", type="string", description="Medical-book search query", required=True),
            ToolParameter(name="search_mode", type="string", description="Search mode, such as embedding or llm", required=False, default="embedding"),
        ]

    # -------------------- index loading --------------------

    def _load_index_if_exists(self):
        if not self.index_dir.exists():
            print(f"[medibook] index not found: {self.index_dir}, will fallback to online traversal.")
            return

        keys_meta_path = self.index_dir / "keys_meta.jsonl"
        keys_emb_path = self.index_dir / "keys_emb.npy"
        leaf_meta_path = self.index_dir / "leaf_meta.jsonl"
        chunks_emb_path = self.index_dir / "chunks_emb.npy"
        chunks_jsonl_path = self.index_dir / "chunks.jsonl"

        if not (keys_meta_path.exists() and keys_emb_path.exists() and leaf_meta_path.exists() and chunks_emb_path.exists() and chunks_jsonl_path.exists()):
            print("[medibook] index files incomplete, fallback.")
            return

        # meta load
        self.keys_meta = [json.loads(line) for line in open(keys_meta_path, "r", encoding="utf-8")]
        self.leaf_meta = [json.loads(line) for line in open(leaf_meta_path, "r", encoding="utf-8")]
        self._chunks_text = chunks_jsonl_path

        for m in self.leaf_meta:
            self._leaf_path_to_id[m["path_str"]] = m["leaf_id"]

        # mmap embeddings
        self.keys_emb = np.load(keys_emb_path, mmap_mode="r")      # float16
        self.chunks_emb = np.load(chunks_emb_path, mmap_mode="r")  # float16

        print(f"[medibook] index loaded: keys={len(self.keys_meta)}, leaves={len(self.leaf_meta)}, chunks={self.chunks_emb.shape[0]}")

    # -------------------- utils --------------------

    @staticmethod
    def _normalize_text(s: str) -> str:
        s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
        s = re.sub(r"\n{3,}", "\n\n", s).strip()
        return s

    @classmethod
    def _extract_overview(cls, text: str) -> str:
        text = cls._normalize_text(text)
        m = re.search(r"(\s*\n+.*?)(\n{2,}\S|\Z)", text, flags=re.S)
        return m.group(1).strip() if m else ""

    def _encode_query(self, q: str) -> np.ndarray:
        q = str(q).strip()
        if not q:
            return np.zeros((1,), dtype=np.float32)

        if q in self._q_cache:
            v = self._q_cache.pop(q)
            self._q_cache[q] = v
            return v

        emb = self.embedding_model.encode([q])
        emb = np.asarray(emb)
        if emb.ndim == 2:
            emb = emb[0]
        emb = emb.astype(np.float32)

        self._q_cache[q] = emb
        if len(self._q_cache) > self._Q_CACHE_MAX:
            self._q_cache.popitem(last=False)
        return emb

    def _get_node_by_path(self, path: List[str]) -> Any:
        node = self.book
        for p in path:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                return None
        return node

    # chunks.jsonl: leaf_id chunk
    # Load text chunks for one leaf from chunks.jsonl.
    def _load_leaf_chunks_text(self, leaf_id: int) -> List[str]:
        out = []
        with open(self._chunks_text, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                if obj["leaf_id"] == leaf_id:
                    out.append(obj["chunk_text"])
        return out

    def _format_topk(self, query: str, path: List[str], book_title: str, chunks: List[str], scores: List[float]) -> str:
        citation_path = " -> ".join(path) if path else "unknown path"
        citation = f"[1] {book_title}/{citation_path}"

        parts: List[str] = []
        parts.append(f"Retrieval topic: {query}")
        parts.append(f"Source citation: {citation}")
        parts.append("")
        parts.append(f"[Top {len(chunks)} most relevant passages]")
        for i, (t, sc) in enumerate(zip(chunks, scores), 1):
            parts.append(f"(Passage {i}, citation={citation})")
            parts.append(self._normalize_text(t))
            parts.append("")
        out = "\n".join(parts).strip()
        if len(out) > self._DEFAULT_MAX_CHARS:
            out = out[:self._DEFAULT_MAX_CHARS].rstrip() + "\n\n(Truncated to keep the most relevant passages and citation information.)"
        return out

    # -------------------- run --------------------

    def run(self, parameters: Dict[str, Any]) -> str:
        query = parameters.get("query")
        if not query:
            return json.dumps({"error": "query is required"}, ensure_ascii=False)

        search_mode = parameters.get("search_mode", "embedding")

        # ========== embedding search ==========
        if search_mode == "embedding" and self.keys_meta is not None and self.keys_emb is not None:
            q_vec = self._encode_query(query)  # (D,)
            # keys_emb: (N, D) float16 -> dot product.
            sims = (self.keys_emb.astype(np.float32) @ q_vec.reshape(-1, 1)).reshape(-1)
            best_kid = int(np.argmax(sims))
            best_path = self.keys_meta[best_kid]["path"]
            best_path_str = self.keys_meta[best_kid]["path_str"]

            node = self._get_node_by_path(best_path)

            # Leaf node.
            if isinstance(node, str):
                leaf_id = self._leaf_path_to_id.get(best_path_str, None)
                book_title = best_path[0] if best_path else ""
                if leaf_id is None:
                    # Fall back if the leaf ID is unavailable.
                    text = self._normalize_text(node)
                    citation = f"[1] {book_title}/{best_path_str}"
                    out = f"Query: {query}\nCitation: {citation}\n\n{text}"
                    if len(out) > self._DEFAULT_MAX_CHARS:
                        out = out[:self._DEFAULT_MAX_CHARS].rstrip() + "\n\n(Truncated.)"
                    return out

                # Rank existing chunk embeddings without encoding chunks again.
                lm = self.leaf_meta[leaf_id]
                start = int(lm["chunk_start"])
                cnt = int(lm["chunk_count"])
                if cnt <= 0:
                    return self._format_topk(str(query), best_path, book_title, [node], [0.0])

                leaf_chunk_emb = self.chunks_emb[start:start+cnt].astype(np.float32)  # (cnt, D)
                csims = (leaf_chunk_emb @ q_vec.reshape(-1, 1)).reshape(-1)
                topk = min(self._DEFAULT_TOP_K, cnt)
                idx = np.argsort(-csims)[:topk]

                # Load chunks for the selected leaf.
                # The offset metadata is not needed for formatting.
                chunk_texts = self._load_leaf_chunks_text(leaf_id)
                top_chunks = [chunk_texts[int(i)] for i in idx]
                top_scores = [float(csims[int(i)]) for i in idx]

                # Include the overview before ranked chunks when available.
                ov = self._extract_overview(node)
                if ov:
                    top_chunks = [ov] + top_chunks
                    top_scores = [top_scores[0] if top_scores else 0.0] + top_scores

                return self._format_topk(str(query), best_path, book_title, top_chunks[:topk], top_scores[:topk])

            # Non-leaf node.
            if isinstance(node, dict):
                book_title = best_path[0] if best_path else ""
                citation = f"[1] {book_title}/{best_path_str}"
                keys = list(node.keys())
                preview = "; ".join(keys[:50])
                more = "" if len(keys) <= 50 else " (showing first 50 keys)"
                return f"Query: {query}\nCitation: {citation}\n\nPreview:\n{preview}{more}"

            return json.dumps({"error": "unsupported node type"}, ensure_ascii=False)

        # ========== fallback ==========
        if search_mode == "embedding":
            return json.dumps({"error": "embedding index is unavailable; run build_medibook_index.py first"}, ensure_ascii=False)

        # ========== LLM mode ==========
        if search_mode == "llm":
            return json.dumps({"error": "LLM search mode is not available in this release; use embedding mode"}, ensure_ascii=False)

        return json.dumps({"error": f"search_mode: {search_mode}"}, ensure_ascii=False)
