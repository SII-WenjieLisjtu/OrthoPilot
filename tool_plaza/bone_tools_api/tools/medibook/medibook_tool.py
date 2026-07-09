"""
medical book检索工具（工具端）
- 推荐：离线 build_medibook_index.py 生成 index 后，server 启动秒开
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
            description="查询医学书籍，获取疾病、药物、症状等医学实体的相关信息"
        )

        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "medibook"
        self.data_dir = Path(data_dir)

        self.book = json.load(open(self.data_dir / "medical_books_content.json", "r", encoding="utf-8"))

        # ---- 只对 query 做 embedding：模型仍需加载一次（很快），但不会全量 tokenize ----
        self.embedding_model = FlagAutoModel.from_finetuned(
            "BAAI/bge-base-zh-v1.5",
            query_instruction_for_retrieval="为这个句子生成表示以用于检索相关文章：",
            use_fp16=True,
            devices=["cpu"],
        )

        try:
            self.chat_model = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE"))
        except Exception as e:
            print(f"初始化OpenAI客户端失败: {e}")
            self.chat_model = None

        # 输出控制
        self._DEFAULT_TOP_K = 5
        self._DEFAULT_MAX_CHARS = 2500

        # 索引（离线生成）
        self.index_dir = Path("/path/to/orthopilot/tool_plaza/bone_tools_api/tools/medibook/index")
        self.keys_meta = None          # list[dict]
        self.keys_emb = None           # np.ndarray (N, D) float16/float32 (mmap)
        self.leaf_meta = None          # list[dict]
        self.chunks_emb = None         # np.ndarray (M, D) mmap
        self._chunks_text = None       # chunks.jsonl 的路径（按需读取）
 
        self._leaf_path_to_id = {}     # path_str -> leaf_id

        self._load_index_if_exists()

        # query embedding LRU（可选，避免同一 query 反复 encode）
        self._q_cache = OrderedDict()
        self._Q_CACHE_MAX = 256

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="query", type="string", description="要查询的医学实体名称", required=True),
            ToolParameter(name="search_mode", type="string", description="检索方式 embedding 或 llm", required=False, default="embedding"),
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
        m = re.search(r"(概述\s*\n+.*?)(\n{2,}\S|\Z)", text, flags=re.S)
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

    # chunks.jsonl 读取：这里做最简单按 leaf_id 扫描取需要的 chunk
    # 如果 chunks.jsonl 很大，建议后续再做“offset 索引”优化；先保证可用。
    def _load_leaf_chunks_text(self, leaf_id: int) -> List[str]:
        out = []
        with open(self._chunks_text, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                if obj["leaf_id"] == leaf_id:
                    out.append(obj["chunk_text"])
        return out

    def _format_topk(self, query: str, path: List[str], book_title: str, chunks: List[str], scores: List[float]) -> str:
        citation_path = " -> ".join(path) if path else "（未知路径）"
        citation = f"[1] 《{book_title}》/{citation_path}"

        parts: List[str] = []
        parts.append(f"检索主题：{query}")
        parts.append(f"来源引用：{citation}")
        parts.append("")
        parts.append(f"【最相关片段 Top{len(chunks)}（按语义相似度排序）】")
        for i, (t, sc) in enumerate(zip(chunks, scores), 1):
            parts.append(f"（片段{i}，引用={citation}）")
            parts.append(self._normalize_text(t))
            parts.append("")
        out = "\n".join(parts).strip()
        if len(out) > self._DEFAULT_MAX_CHARS:
            out = out[:self._DEFAULT_MAX_CHARS].rstrip() + "\n\n（已截断：仅保留最相关片段与引用信息）"
        return out

    # -------------------- run --------------------

    def run(self, parameters: Dict[str, Any]) -> str:
        query = parameters.get("query")
        if not query:
            return json.dumps({"error": "参数query是必需的"}, ensure_ascii=False)

        search_mode = parameters.get("search_mode", "embedding")

        # ========== embedding（走离线索引，最快） ==========
        if search_mode == "embedding" and self.keys_meta is not None and self.keys_emb is not None:
            q_vec = self._encode_query(query)  # (D,)
            # keys_emb: (N, D) float16 -> dot
            sims = (self.keys_emb.astype(np.float32) @ q_vec.reshape(-1, 1)).reshape(-1)
            best_kid = int(np.argmax(sims))
            best_path = self.keys_meta[best_kid]["path"]
            best_path_str = self.keys_meta[best_kid]["path_str"]

            node = self._get_node_by_path(best_path)

            # 命中 leaf
            if isinstance(node, str):
                leaf_id = self._leaf_path_to_id.get(best_path_str, None)
                book_title = best_path[0] if best_path else "医学书籍知识库"
                if leaf_id is None:
                    # 兜底：没找到 leaf_id 就直接截断返回
                    text = self._normalize_text(node)
                    citation = f"[1] 《{book_title}》/{best_path_str}"
                    out = f"检索主题：{query}\n来源引用：{citation}\n\n{text}"
                    if len(out) > self._DEFAULT_MAX_CHARS:
                        out = out[:self._DEFAULT_MAX_CHARS].rstrip() + "\n\n（已截断）"
                    return out

                # 用 chunks_emb 全量点乘取 TopK（无需 encode chunks）
                lm = self.leaf_meta[leaf_id]
                start = int(lm["chunk_start"])
                cnt = int(lm["chunk_count"])
                if cnt <= 0:
                    return self._format_topk(str(query), best_path, book_title, [node], [0.0])

                leaf_chunk_emb = self.chunks_emb[start:start+cnt].astype(np.float32)  # (cnt, D)
                csims = (leaf_chunk_emb @ q_vec.reshape(-1, 1)).reshape(-1)
                topk = min(self._DEFAULT_TOP_K, cnt)
                idx = np.argsort(-csims)[:topk]

                # 读取对应 chunk 文本（简易实现：按 leaf_id 扫描 chunks.jsonl）
                # 如果你数据巨大，下一步可以改成“offset 索引”避免扫描
                chunk_texts = self._load_leaf_chunks_text(leaf_id)
                top_chunks = [chunk_texts[int(i)] for i in idx]
                top_scores = [float(csims[int(i)]) for i in idx]

                # （可选）把“概述”放最前面：这里直接从原文抽
                ov = self._extract_overview(node)
                if ov:
                    top_chunks = [ov] + top_chunks
                    top_scores = [top_scores[0] if top_scores else 0.0] + top_scores

                return self._format_topk(str(query), best_path, book_title, top_chunks[:topk], top_scores[:topk])

            # 命中章节（非 leaf）
            if isinstance(node, dict):
                book_title = best_path[0] if best_path else "医学书籍知识库"
                citation = f"[1] 《{book_title}》/{best_path_str}"
                keys = list(node.keys())
                preview = "；".join(keys[:50])
                more = "" if len(keys) <= 50 else "（仅展示前50项）"
                return f"检索主题：{query}\n来源引用：{citation}\n\n命中章节但未到具体正文，可继续查询以下子标题：\n{preview}{more}"

            return json.dumps({"error": "命中节点类型异常"}, ensure_ascii=False)

        # ========== fallback（无索引时，老逻辑/或你可以直接报错提示先建索引） ==========
        if search_mode == "embedding":
            return json.dumps({"error": "未检测到离线索引，请先运行 build_medibook_index.py 生成 index/ 目录"}, ensure_ascii=False)

        # ========== llm 模式（保留你原逻辑，略；你若还要我也可把 llm 分层选择补回） ==========
        if search_mode == "llm":
            return json.dumps({"error": "llm 模式未在该版本启用（建议优先用离线 embedding 索引）"}, ensure_ascii=False)

        return json.dumps({"error": f"未知search_mode: {search_mode}"}, ensure_ascii=False)
