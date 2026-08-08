# KB Server knowledge corpus (eval fixture)

> This file is the eval corpus. Each section is one "document" with id and
> text. The evaluator reads this corpus via the API and checks that the
> retrieved snippets contain the expected substrings.

## doc:project-root
The project root structure includes `desktop/` for the Electron + React +
TypeScript application and `server/` for the Python FastAPI service. The
kb-server package lives under `server/app/` and is exposed as the running
process.

## doc:add-datasource
To add a new datasource, implement the `DataSource` ABC and call
`register_datasource(type_name, cls)`. The adapter class must implement
`add(chunks)`, `search(vector, top_k, filter)`, `delete(ids)`, and
`health()`. A `DatasourceConfig` with `name` and `type` is passed to the
constructor.

## doc:embedder
The default embedding model is `BAAI/bge-m3` with 1024 dimensions, served
locally via sentence-transformers. The embedder is lazily loaded on first
use. The OpenAI-compatible backend talks to any /embeddings endpoint.

## doc:file-types
Supported file types for import are excel (xlsx, xls) via openpyxl, word
(docx, doc) via python-docx, pdf via pdfplumber, and markdown via
markdown-it-py.

## doc:chunker
The text chunker is paragraph-aware with a default chunk_size of 1200
characters and an overlap of 200 characters. Overlap preserves context at
chunk boundaries. Long paragraphs are hard-split on sentence or word
boundaries.

## doc:postgres
The PostgreSQL adapter uses the pgvector extension. The schema includes
a `vector(dim)` column with an ivfflat index for cosine distance. JSONB is
used for metadata filtering.

## doc:elasticsearch
The Elasticsearch adapter uses the dense_vector field type with cosine
similarity. Queries use the knn clause. Metadata filtering is supported via
the filter parameter in knn queries.

## doc:mysql
The MySQL adapter stores vectors in a JSON column. Cosine similarity is
computed in Python after a bounded scan. This is recommended for small
datasets only (less than 100k vectors).

## doc:milvus
The vector database adapter supports a Milvus backend via pymilvus. The
default collection is created with COSINE metric and the configured
dimension.

## doc:health
The /v1/health endpoint returns the server status, embed backend, embed
dimension, and the list of registered datasource types.