# Error / Warning Taxonomy (v0.1)

Each issue has a stable `id`, `severity` (`info|warn|error`), human `message`, and optional `hint`.

| id                         | severity | message                                   | path/loc example           |
|---------------------------|----------|-------------------------------------------|----------------------------|
| column.missing_required   | error    | Required column is missing                 | `columns/sample_id`        |
| column.name_mismatch      | warn     | Column name differs from expected pattern  | `columns/SampleID`         |
| row.duplicate_key         | warn     | Duplicate value in key column              | `rows/123` (col: sample_id)|
| cell.empty_required       | error    | Empty cell in required column              | `rows/45/columns/sample_id`|

Deterministic ordering: sort by `(path, id, severity)`.
