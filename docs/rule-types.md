# Rule types reference

This document describes all available rule types that can be used in FAIRy rulepacks. Each rule type validates a specific aspect of your data.

## Available rule types

FAIRy supports the following rule types:

1. [`required`](#required) - Ensures specified columns exist and are non-empty
2. [`unique`](#unique) - Ensures values in specified columns are unique
3. [`enum`](#enum) - Ensures values are in an allowed list
4. [`range`](#range) - Ensures numeric values are within min/max bounds
5. [`dup` / `no_duplicate_rows`](#dup--no_duplicate_rows) - Ensures no duplicate rows based on specified keys
6. [`foreign_key`](#foreign_key) - Ensures referential integrity across tables
7. [`url`](#url) - Validates URL format and allowed schemes
8. [`non_empty_trimmed`](#non_empty_trimmed) - Ensures a column is non-empty after trimming whitespace
9. ['regex`](#regex) - Validates string formats or flags forbidden patterns using regular expressions

---

## `required`

Ensures that specified columns exist in the table and that all rows have non-empty values in those columns.

### Configuration

- `pattern` (string): File pattern to match (e.g., `"*.csv"`, `"artists.csv"`)
- `columns` (list of strings): List of column names that must be present and non-empty

### Example

```yaml
- id: record-metadata-minimum
  type: required
  severity: warn
  config:
    pattern: "raw*.csv"
    columns:
      - title
      - creator
```

### Example with remediation links

When datasets include a column with external URLs (e.g., portal links), you can configure remediation links to help users fix validation failures:

```yaml
- id: primary_id_required
  type: required
  severity: fail
  columns: ["primary_id"]
  remediation_link_column: "external_url"
  remediation_link_label: "Open record in portal"
```

When this rule fails, the report includes remediation links for each failing row. In markdown reports, these appear as clickable links: `[Open record in portal](https://example.com/record/123)`.

### What it checks

- The specified columns exist in the table
- All rows have non-empty values (not null, not empty string, not whitespace-only) in those columns

### Failure conditions

- Column is missing from the table
- One or more rows have empty/null values in a required column

---

## `unique`

Ensures that values in the specified column(s) are unique across all rows. For multiple columns, checks that the combination of values is unique.

### Configuration

- `pattern` (string): File pattern to match
- `columns` (list of strings): Column name(s) that must have unique values

### Example

```yaml
- id: uniq_artist_id
  type: unique
  severity: fail
  config:
    pattern: "artists.csv"
    columns: ["id"]
```

### What it checks

- Each value (or combination of values) in the specified column(s) appears only once

### Failure conditions

- Duplicate values found in the specified column(s)

---

## `enum`

Ensures that values in a column are from a predefined allowed list. Supports optional normalization (case-insensitive matching, trimming) for flexible validation.

### Configuration

- `pattern` (string): File pattern to match
- `column` (string): Column name to validate
- `allow` (list): List of allowed values
- `normalize` (dict, optional): Normalization options
  - `casefold` (boolean): Convert to lowercase before comparison (default: `false`)
  - `trim` (boolean): Trim whitespace before comparison (default: `false`)

### Example

```yaml
- id: species_enum
  type: enum
  severity: fail
  config:
    pattern: "penguins*.csv"
    column: species
    allow: ["Adelie", "Chinstrap", "Gentoo"]

- id: sex_enum
  type: enum
  severity: warn
  config:
    pattern: "penguins*.csv"
    column: sex
    allow: ["male", "female"]
    normalize: { casefold: true, trim: true }
```

### What it checks

- All values in the specified column are in the allowed list
- If normalization is enabled, values are normalized before comparison

### Failure conditions

- Value found that is not in the allowed list (after normalization, if enabled)

---

## `range`

Ensures that numeric values in a column fall within specified minimum and/or maximum bounds.

### Configuration

- `pattern` (string): File pattern to match
- `column` (string): Column name to validate
- `min` (number, optional): Minimum allowed value
- `max` (number, optional): Maximum allowed value
- `inclusive` (boolean, optional): Whether bounds are inclusive (default: `true`)

### Example

```yaml
- id: bill_len_range
  type: range
  severity: warn
  config:
    pattern: "penguins*.csv"
    column: bill_length_mm
    min: 30
    max: 60
    inclusive: true

- id: price_range
  type: range
  severity: fail
  config:
    pattern: "artworks_*.csv"
    column: price
    min: 0
    inclusive: true
```

### What it checks

- All numeric values in the specified column are within the allowed range
- Non-numeric values are treated as out of bounds

### Failure conditions

- Value is less than `min` (or less than or equal if `inclusive: false`)
- Value is greater than `max` (or greater than or equal if `inclusive: false`)
- Value cannot be converted to a number

---

## `dup` / `no_duplicate_rows`

Ensures that no two rows have identical values across all specified key columns. These two type names are equivalent (`dup` is an alias for `no_duplicate_rows`).

### Configuration

- `pattern` (string): File pattern to match
- `keys` (list of strings): Column names that together form a composite key

### Example

```yaml
- id: no_dups
  type: no_duplicate_rows
  severity: fail
  config:
    pattern: "penguins*.csv"
    keys: [species, island, bill_length_mm, bill_depth_mm, flipper_length_mm, body_mass_g, sex, year]
```

### What it checks

- No two rows have identical values for all specified key columns

### Failure conditions

- Duplicate rows found with identical values across all key columns

---

## `foreign_key`

Ensures referential integrity between two tables. Validates that all values in a source column exist in a target column of another table.

### Configuration

- `pattern` (string): File pattern to match (typically the source table)
- `from` (dict): Source table and column
  - `table` (string): Name of the source table (must match an input table name)
  - `field` (string): Column name in the source table
- `to` (dict): Target table and column
  - `table` (string): Name of the target table (must match an input table name)
  - `field` (string): Column name in the target table

### Example

```yaml
- id: artworks_artist_fk
  type: foreign_key
  severity: fail
  config:
    pattern: "artworks_*.csv"
    from: { table: artworks, field: artist_id }
    to:   { table: artists,  field: id }
```

### What it checks

- Every non-null value in the source column exists in the target column
- Both tables must be provided as named inputs (using `--inputs` flag)

### Failure conditions

- Value in source column does not exist in target column
- Source or target table/column not found

### Notes

- Requires multi-input validation (both tables must be provided)
- Table names in `from.table` and `to.table` must match the names used in `--inputs name=path` flags

---

## `url`

Validates that values in a column are valid URLs with allowed URL schemes (e.g., `http`, `https`).

### Configuration

- `pattern` (string): File pattern to match
- `column` (string): Column name to validate
- `schemes` (list of strings, optional): Allowed URL schemes (default: `["http", "https"]`)

### Example

```yaml
- id: homepage_urls
  type: url
  severity: warn
  config:
    pattern: "artists.csv"
    column: homepage
    schemes: ["http", "https"]
```

### What it checks

- Values are valid URL syntax
- URL scheme is in the allowed list (if specified)
- URL has either a network location (`netloc`) or a path component

### Failure conditions

- Invalid URL syntax
- URL scheme not in allowed list
- Empty URL (no netloc and no path)

---

## `non_empty_trimmed`

Ensures that a column contains non-empty values after trimming whitespace. This is stricter than `required` because it also rejects whitespace-only values.

### Configuration

- `pattern` (string): File pattern to match
- `column` (string): Column name to validate

### Example

```yaml
- id: title_non_empty
  type: non_empty_trimmed
  severity: warn
  config:
    pattern: "artworks_*.csv"
    column: title
```

### What it checks

- All values in the specified column are non-empty after trimming leading and trailing whitespace

### Failure conditions

- Value is null/NaN
- Value is empty string after trimming whitespace
---

## `regex`

Validates string formats or detects forbidden patterns using a regular expression.

This rule is useful for IDs (accessions, specimen IDs, sample IDs), code-like fields with fixed syntax, and for flagging control characters or disallowed tokens.

### Configuration

- `pattern` (string): File pattern to match
- `column` (string): Column name to validate
- `regex` (string): Regular expression pattern (Python `re` syntax)
- `mode` (string, optional): How to interpret the regex (default: `not_matches`)
  - `not_matches`: flag non-empty values that do **not** match the regex (format enforcement)
  - `matches`: flag non-empty values that **do** match the regex (forbidden pattern detection)
- `ignore_empty` (boolean, optional): Whether to ignore empty/whitespace-only/NA values (default: `true`)
  - If `true`, empty values are skipped by this rule. Pair with `required` or `non_empty_trimmed` if empties should be flagged.

### Examples

#### Enforce an ID format (`mode: not_matches`)

```yaml
- id: sample_id_format
  type: regex
  severity: fail
  config:
    pattern: "data*.csv"
    column: sample_id
    regex: "^[A-Z]{3}-[0-9]{5}-[0-9]{3}$"
    mode: not_matches
    ignore_empty: true
```

#### Flag forbidden control characters (`mode: matches`)
```yaml
- id: product_name_no_control_chars
  type: regex
  severity: warn
  config:
    pattern: "annotations*.csv"
    column: product_name
    regex: "[\\t\\r\\n\\x00-\\x1F\\x7F]"
    mode: matches
    ignore_empty: true

```
### What it checks

- For `mode: not_matches`: values must match the **entire** string pattern (full match)
- For `mode: matches`: values are flagged if the regex is found **anywhere** in the string

#### Failure conditions
- Column is missing from the table
- Regex is missing or invalid
- Value violates the rule according to `mode` (empty values are ignored when `ignore_empty: true`)

---

## Rule structure

All rules follow this basic structure:

```yaml
- id: <unique-rule-identifier>
  type: <rule-type>
  severity: <fail|warn>
  config:
    pattern: <file-pattern>
    # ... type-specific configuration ...
```

### Common fields

- `id` (string, required): Unique identifier for the rule
- `type` (string, required): One of the rule types listed above
- `severity` (string, required): `fail` or `warn`
  - `fail`: Rule violations block submission (`submission_ready: false`)
  - `warn`: Rule violations are reported but don't block submission
- `config` (dict, required): Type-specific configuration (always includes `pattern`)
- `remediation_link_column` (string, optional): Column name containing URLs for fixing failures. When a rule fails, values from this column are included in the failure evidence so users can click through to fix issues in the source system.
- `remediation_link_label` (string, optional): Human-readable label for the remediation link (e.g., "Open record in portal"). Defaults to the column name if not specified.

### YAML syntax tips

When listing columns in YAML, always include a space after the dash:

```yaml
# ✅ Correct
columns:
  - id
  - name

# ❌ Wrong (missing space - YAML will treat "-id" as a string literal)
columns:
  -id
  -name
```

Alternatively, use inline list syntax which is less error-prone:

```yaml
columns: ["id", "name"]
```

### File patterns

The `pattern` field in `config` uses shell-style glob matching:
- `"artists.csv"` - Exact filename match
- `"*.csv"` - All CSV files
- `"penguins*.csv"` - Files starting with "penguins" and ending with ".csv"
- `"artworks_*.csv"` - Files starting with "artworks_" and ending with ".csv"

Patterns are matched against the filename only (not the full path).

---

## See also

- [Getting started](./getting-started.md) - Installation and first steps
- [CLI usage](./cli.md) - Command-line interface reference
- [Kata gallery](./katas/index.md) - Example rulepacks and datasets
