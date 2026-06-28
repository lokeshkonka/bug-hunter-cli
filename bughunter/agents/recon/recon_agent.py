import os
from pathlib import Path
import asyncio
import uuid
from bughunter.core.events.emitter import AgentEventEmitter
from bughunter.models.event import EventType
from bughunter.agents.recon.manifest_builder import ManifestBuilder
from bughunter.storage.recon_store import ReconStore

class ReconAgent:
    def __init__(self, run_id: str, emitter: AgentEventEmitter, db_path: str):
        self.run_id = run_id
        self.emitter = emitter
        self.db_path = db_path
        self.recon_store = ReconStore(db_path)
        
    async def run(self, project_root: str):
        await self.emitter.emit(self.run_id, EventType.phase_started, "Recon Phase")
        await self.emitter.emit(self.run_id, EventType.tool_started, "Building codebase manifest")
        
        builder = ManifestBuilder(project_root)
        manifest = await asyncio.to_thread(builder.build)
        
        await self.emitter.emit(self.run_id, EventType.tool_completed, f"Manifest built. Found {len(manifest.scored_files)} relevant files out of {len(manifest.scored_files) + len(manifest.excluded_files)} total files.")
        
        # Save to SQLite DB
        await self.emitter.emit(self.run_id, EventType.tool_started, "Saving index to database")
        
        for f_info in manifest.scored_files:
            file_id = str(uuid.uuid4())
            await self.recon_store.insert_file(
                file_id=file_id,
                run_id=self.run_id,
                path=f_info.file_path,
                language="unknown", # We can detect later
                relevance_score=f_info.score,
                excluded=False,
                excluded_reason=""
            )
            # Create an index entry for the file
            entry_id = str(uuid.uuid4())
            tags_str = ",".join(f_info.tags)
            await self.recon_store.insert_index_entry(
                entry_id=entry_id,
                run_id=self.run_id,
                file_id=file_id,
                symbol="file_summary",
                line_start=1,
                line_end=1,
                security_relevance="high" if f_info.score > 0.5 else "medium",
                tags=tags_str,
                test_category="static"
            )
            
        for excl_file in manifest.excluded_files:
            file_id = str(uuid.uuid4())
            await self.recon_store.insert_file(
                file_id=file_id,
                run_id=self.run_id,
                path=excl_file,
                language="unknown",
                relevance_score=0.0,
                excluded=True,
                excluded_reason="Below relevance threshold or ignored extension"
            )
            
        await self.emitter.emit(self.run_id, EventType.tool_completed, "Index saved to database")
        
        # Write index.md
        index_dir = Path(f".bughunter/runs/{self.run_id}")
        index_dir.mkdir(parents=True, exist_ok=True)
        index_path = index_dir / "index.md"
        
        with open(index_path, "w") as f:
            f.write(f"# Codebase Index for `{project_root}`\n\n")
            f.write(f"## Project Summary\n")
            f.write(f"- **Languages Detected**: {', '.join(manifest.languages) if manifest.languages else 'None'}\n")
            f.write(f"- **Frameworks Detected**: {', '.join(manifest.frameworks) if manifest.frameworks else 'None'}\n")
            f.write(f"- **Total Scanned Files**: {len(manifest.scored_files)}\n")
            f.write(f"- **Total Excluded Files**: {len(manifest.excluded_files)}\n\n")
            
            f.write("## Security-Sensitive File Index (Score >= 0.3)\n")
            for f_info in sorted(manifest.scored_files, key=lambda x: x.score, reverse=True):
                f.write(f"- **`{f_info.file_path}`** (Score: {f_info.score})\n")
                f.write(f"  - **Tags**: {', '.join(f_info.tags)}\n")
                f.write(f"  - **Reasons**: {', '.join(f_info.reasons)}\n")
                
        await self.emitter.emit(self.run_id, EventType.tool_completed, f"Wrote index.md to {index_path}")
        
        # Semantic Vector DB Ingestion
        await self.emitter.emit(self.run_id, EventType.tool_started, "Ingesting to local Vector DB (ChromaDB) for RAG")
        try:
            from bughunter.storage.vector_store import VectorStore
            vs = VectorStore()
            chunks = await asyncio.to_thread(vs.ingest_directory, project_root)
            await self.emitter.emit(self.run_id, EventType.tool_completed, f"Vector ingestion complete: {chunks} chunks indexed.")
        except Exception as e:
            await self.emitter.emit(self.run_id, EventType.error, f"Vector ingestion skipped or failed: {e}")
            
        return manifest
