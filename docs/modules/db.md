# db
`from corio import db`

Database helper package namespace.

- Base namespace uses `db`.
- Document-model integrations use `db.document`.

## Search chunk retrieval

`corio.db.search.document.Document.get_chunks` accepts an optional Qdrant `Filter` as `runtime_filter`. Corio ANDs it with the document ID and chunk-index conditions. Use it when several logical collections share one physical Qdrant collection; filtering by the logical collection ID keeps chunk retrieval scoped to the requested collection.


