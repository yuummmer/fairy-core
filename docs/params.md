# Parameter files (--param-file)

The `--param-file` flag allows you to pass tunable parameters to FAIRy validation runs. Parameters are loaded from a YAML file and injected into the validation context, making it easy to customize rule behavior without modifying rulepacks.

## Overview

When you provide a `--param-file`, FAIRy:
1. Loads the YAML file and parses it as a dictionary
2. Injects the parameters into the validation context at `ctx["params"]`
3. Makes them available to validation rules during execution

## Basic usage

```bash
fairy preflight \
  --rulepack path/to/rulepack.json \
  --samples path/to/samples.tsv \
  --files path/to/files.tsv \
  --out path/to/report.json \
  --param-file path/to/params.yml
```

## Parameter file format

Parameter files must be valid YAML with a top-level mapping (dictionary). Each key-value pair becomes a parameter accessible via `ctx["params"]`.

### Example parameter file

```yaml
min_year: 2007
max_file_size_mb: 500
strict_mode: true
allowed_formats:
  - fastq
  - bam
  - sam
```

## Accessing parameters in rules

Parameters are available to validation functions through the `ctx` parameter. Access them using:

```python
params = (ctx or {}).get("params", {}) or {}
min_year = params.get("min_year")
```

### Example: Using a parameter in a validation rule

Here's a conceptual example of how a rule might use the `min_year` parameter:

```yaml
# rulepack.yml
rules:
  - id: year_range_check
    type: range
    severity: fail
    config:
      column: year
      # In practice, the rule implementation would read:
      # min = ctx["params"].get("min_year")
      # from the validation context
```

The actual rule implementation would access the parameter like this:

```python
def check_year_range(df, column, ctx=None):
    params = (ctx or {}).get("params", {}) or {}
    min_year = params.get("min_year")
    # Use min_year in validation logic...
```

## Demo file

A minimal example parameter file is available at [`demos/params/penguins.yml`](../demos/params/penguins.yml):

```yaml
min_year: 2007
```

## Error messages

FAIRy provides clear error messages when parameter files have issues:

### Missing file

If the parameter file doesn't exist:

```
Param file not found: path/to/missing.yml
```

### Parse error

If the YAML file is malformed:

```
Failed to parse params YAML at path/to/bad.yml: <error details>
```

### Non-mapping top-level

If the YAML file's top-level is not a dictionary (e.g., a list or scalar):

```
Top-level YAML must be a mapping (dict). Got: <type>
```

## Where parameters are stored

Parameters are loaded from the YAML file and stored in the validation context:

- **Location**: `ctx["params"]`
- **Type**: `dict[str, Any]`
- **Default**: Empty dictionary `{}` if no `--param-file` is provided

The parameters are also included in the report metadata as `params_sha256` (configuration identity: a SHA-256 hash of the canonical JSON serialization) to track when the same rulepack is run with different parameters.

## See also

- [CLI usage](./cli.md) for command-line reference
- [Getting started](./getting-started.md) for installation and first steps
- [Rule types reference](./rule-types.md) for available rule types
