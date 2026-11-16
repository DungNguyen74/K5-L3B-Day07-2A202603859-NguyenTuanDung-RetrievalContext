"""Module implementing 3 Retrieval Methods for Day 7:
1. LexicalRetriever (TF-IDF / BM25)
2. DenseRetriever (ChromaDB + all-MiniLM-L6-v2 384d)
3. HybridRetriever (Dense + Lexical via Reciprocal Rank Fusion - RRF)
"""
import math
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


def tokenize(text: str) -> list[str]:
    return re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold())


def hit(chunk: dict[str, Any], gold: list[dict[str, Any]]) -> bool:
    return any(
        chunk['source_id'] == g['source_id']
        and chunk['page'] == g['page']
        and g['evidence'] in chunk['text']
        for g in gold
    )


def pack_context(results: list[dict[str, Any]], budget: int = 800) -> tuple[str, list[str]]:
    blocks, ids, seen = [], [], set()
    for c in results:
        if c['id'] in seen:
            continue
        seen.add(c['id'])
        block = f"[{c['id']} | {c['source']} | page {c['page']}]\n{c['text']}"
        if len('\n\n'.join(blocks + [block])) <= budget:
            blocks.append(block)
            ids.append(c['id'])
    return '\n\n'.join(blocks), ids


class LexicalRetriever:
    """TF-IDF lexical retrieval conforming to Day 7 Retriever protocol."""
    
    def __init__(self, chunks: list[dict[str, Any]]):
        self.chunks = chunks
        self.chunk_by_id = {c['id']: c for c in chunks}
        counts = [Counter(tokenize(c['text'])) for c in chunks]
        df = Counter(term for row in counts for term in row)
        self.idf = {term: math.log((1 + len(chunks)) / (1 + count)) + 1 for term, count in df.items()}
        self.vectors = [self._vector(row) for row in counts]

    def _vector(self, counts: Counter) -> dict[str, float]:
        vector = {term: count * self.idf[term] for term, count in counts.items() if term in self.idf}
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1
        return {term: value / norm for term, value in vector.items()}

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        q_vec = self._vector(Counter(tokenize(query)))
        results = []
        for chunk, vector in zip(self.chunks, self.vectors):
            if filters:
                meta = chunk.get('metadata', {})
                if not all(meta.get(k) == v for k, v in filters.items()):
                    continue
            score = sum(value * vector.get(term, 0) for term, value in q_vec.items())
            if score > 0:
                results.append({**chunk, 'score': score, 'strategy': 'tfidf'})
        return sorted(results, key=lambda c: (-c['score'], c['id']))[:top_k]


class DenseRetriever:
    """Dense retrieval using ChromaDB persistent vector store and all-MiniLM-L6-v2."""
    
    def __init__(self, persist_dir: str | Path = "starter/chroma_data", collection_name: str = "strategy_b"):
        self.persist_dir = str(Path(persist_dir).resolve())
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.ef = DefaultEmbeddingFunction()
        self.collection = self.client.get_collection(collection_name, embedding_function=self.ef)

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        where_clause = None
        if filters:
            if len(filters) == 1:
                k, v = next(iter(filters.items()))
                where_clause = {k: {"$eq": v}}
            else:
                where_clause = {"$and": [{k: {"$eq": v}} for k, v in filters.items()]}
                
        res = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_clause
        )
        
        results = []
        if res and res["ids"] and res["ids"][0]:
            count = len(res["ids"][0])
            for i in range(count):
                cid = res["ids"][0][i]
                doc = res["documents"][0][i]
                dist = res["distances"][0][i]
                meta = res["metadatas"][0][i] or {}
                # Cosine distance to similarity: 1 - distance
                sim_score = max(0.0, 1.0 - dist)
                results.append({
                    "id": cid,
                    "text": doc,
                    "source_id": meta.get("document_id", "wb_annual_report"),
                    "source": meta.get("source", "data/world_bank_annual_report.pdf"),
                    "page": int(meta.get("page", meta.get("physical_page", 1))),
                    "metadata": meta,
                    "score": sim_score,
                    "distance": dist,
                    "strategy": "dense_chroma"
                })
        return results


class HybridRetriever:
    """Hybrid retrieval combining Dense (ChromaDB) and Lexical (TF-IDF) via Reciprocal Rank Fusion (RRF)."""
    
    def __init__(self, dense_retriever: DenseRetriever, lexical_retriever: LexicalRetriever, rrf_k: int = 60, pool_size: int = 15):
        self.dense = dense_retriever
        self.lexical = lexical_retriever
        self.rrf_k = rrf_k
        self.pool_size = pool_size

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        # Fetch candidate pools from both retrievers
        dense_candidates = self.dense.search(query, filters=filters, top_k=self.pool_size)
        lexical_candidates = self.lexical.search(query, filters=filters, top_k=self.pool_size)
        
        # Calculate RRF scores: RRF(d) = sum(1 / (k + rank))
        scores: dict[str, float] = {}
        chunk_map: dict[str, dict[str, Any]] = {}
        
        for rank, c in enumerate(dense_candidates, start=1):
            cid = c['id']
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))
            chunk_map[cid] = c
            
        for rank, c in enumerate(lexical_candidates, start=1):
            cid = c['id']
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))
            if cid not in chunk_map:
                chunk_map[cid] = c
                
        # Sort by RRF score descending
        sorted_ids = sorted(scores.keys(), key=lambda x: (-scores[x], x))
        
        results = []
        for cid in sorted_ids[:top_k]:
            c = dict(chunk_map[cid])
            c['score'] = scores[cid]
            c['strategy'] = 'hybrid_rrf'
            results.append(c)
            
        return results
