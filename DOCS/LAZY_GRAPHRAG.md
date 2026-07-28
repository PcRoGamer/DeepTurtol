# LazyGraphRAG

LazyGraphRAG is DeepTutor's local, incremental retrieval engine. It persists a
standard vector index at ingestion and creates an entity co-occurrence graph
only from the chunks retrieved for the current question.

This makes it a good default for knowledge bases that change frequently:
uploads do not require an LLM graph-extraction pass, while retrieval still
exposes entities and relationships for the chat capability to use as evidence.

## When to use it

Use LazyGraphRAG when you want fast, local ingestion and incremental updates,
especially when DeepTutor's chat LLM will write the final answer. The engine
returns grounded context, sources, entities, and relationships; the chat model
then synthesizes the user-facing response.

Choose LightRAG instead only when an LLM-extracted persistent graph has shown a
measurable retrieval advantage for relationship-heavy or multi-hop material.
It has higher ingestion cost and depends on the configured RAG completion
model.

## Create a knowledge base

Select `lazygraphrag` as the provider when creating a KB in the application, or
pass it explicitly through the Python API:

```python
from deeptutor.services.rag.service import RAGService

service = RAGService(provider="lazygraphrag")
await service.initialize("course-notes", ["lecture-1.pdf"])
await service.add_documents("course-notes", ["lecture-2.pdf"])

result = await service.search("How does the method handle incremental updates?", "course-notes")
print(result["content"])
```

Documents follow DeepTutor's normal ingestion path. Parser-backed formats such
as PDF and Office files use the configured document parser; text and image
handling follows the same shared file routing used by the other local engines.

## Result shape

`search()` returns the standard DeepTutor retrieval envelope:

- `content` / `answer`: grounded retrieved context for the chat LLM.
- `sources`: the selected chunks and their provenance.
- `entities`: terms extracted from the retrieved candidate set.
- `relationships`: weighted co-occurrences within that same set.

The graph is deliberately query-scoped. It does not claim global, LLM-authored
facts about the entire KB; it is a transparent ranking aid over the evidence
already retrieved by the vector index.

## Lifecycle and persistence

LazyGraphRAG supports create, incremental add, search, force reindex, linked
KBs, readiness inspection, and deletion through the normal `RAGService`
contract. Its provider metadata is stored with the versioned vector index, so
DeepTutor can identify and reopen the correct engine after a restart.

Force reindex is the normal `initialize()` operation with the full file list.
It creates a fresh index version; use `add_documents()` only for new files.

## Verified E2E lifecycle

The provider has been exercised with the configured Docling parser across a
six-PDF lifecycle: create with one file, add two, add three, force reindex all
six, retrieve three factual answers, and delete the KB. The automated
service-lifecycle regression test lives in
`tests/services/rag/test_lazygraphrag_pipeline.py`.
