import os
from pathlib import Path
import chromadb
from typing import List

class VectorStore:
    def __init__(self, persist_directory: str = ".bughunter/vector_store"):
        self.persist_directory = persist_directory
        # Ensure directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(name="codebase")
        
    def _chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 300) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start:start + chunk_size])
            start += chunk_size - overlap
        return chunks

    def ingest_directory(self, root_path: str) -> int:
        ignore_dirs = {".git", ".bughunter", "__pycache__", "node_modules", "venv", ".venv", ".next", "dist", "build", "out"}
        ignore_exts = {".pyc", ".jpg", ".png", ".pdf", ".zip", ".tar", ".gz", ".sqlite3", ".exe", ".dll", ".so", ".dylib", ".class"}
        
        documents = []
        metadatas = []
        ids = []
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
            
            for file in filenames:
                ext = Path(file).suffix
                if ext in ignore_exts:
                    continue
                    
                file_path = os.path.join(dirpath, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    if not content.strip():
                        continue
                        
                    chunks = self._chunk_text(content)
                    for i, chunk in enumerate(chunks):
                        documents.append(chunk)
                        metadatas.append({"file": file_path, "chunk": i})
                        ids.append(f"{file_path}_{i}")
                except Exception:
                    # Skip unreadable files
                    continue
                    
        if documents:
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                self.collection.upsert(
                    documents=documents[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size],
                    ids=ids[i:i+batch_size]
                )
        return len(documents)

    def search(self, query: str, n_results: int = 5) -> List[str]:
        count = self.collection.count()
        if count == 0:
            return []
            
        results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, count)
        )
        
        formatted_results = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            for doc, meta in zip(docs, metas):
                formatted_results.append(f"--- File: {meta['file']} ---\n{doc}\n")
                
        return formatted_results
