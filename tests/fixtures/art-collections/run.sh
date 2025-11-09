#!/usr/bin/env bash
set -euo pipefail

# PASS example (FK satisfied)
fairy validate \
  --rulepack tests/fixtures/art-collections/rulepack.yaml \
  --inputs artworks=tests/fixtures/art-collections/artworks_pass.csv \
  --inputs artists=tests/fixtures/art-collections/artists.csv \
  --report-json tests/fixtures/art-collections/out_pass.json

# FAIL example (missing artistId)
set +e
fairy validate \
  --rulepack tests/fixtures/art-collections/rulepack.yaml \
  --inputs artworks=tests/fixtures/art-collections/artworks_fail_missing_artist.csv \
  --inputs artists=tests/fixtures/art-collections/artists.csv \
  --report-json tests/fixtures/art-collections/out_fail.json
echo "FAIL example exit code: $?"
