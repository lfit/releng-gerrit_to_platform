# Gerrit JSON Validation Examples

This directory contains validation scripts for the `gerrit_json` consolidated variable that encapsulates all Gerrit event data in a single JSON object.

## Overview

The `gerrit_json` variable consolidates all individual `GERRIT_*` variables into a single JSON object with snake_case keys. This reduces the number of workflow inputs and makes it easier to pass Gerrit event data to downstream workflows.

## JSON Schema

The `gerrit_json` object has the following structure:

```json
{
  "branch": "string (required)",
  "change_id": "string (required)",
  "change_number": "string (required)",
  "change_url": "string (required)",
  "event_type": "string (required, one of: patchset-created, change-merged, comment-added)",
  "patchset_number": "string (required)",
  "patchset_revision": "string (required)",
  "project": "string (required)",
  "refspec": "string (required)",
  "comment": "string (optional, only for comment-added events)"
}
```

## Validation Scripts

### Shell Script (validate-json.sh)

Uses `jq` to validate the JSON structure.

**Requirements:**
- `jq` must be installed (`apt-get install jq` on Debian/Ubuntu, `brew install jq` on macOS)

**Usage:**
```bash
./validate-json.sh '{"branch":"master","change_id":"I123...","change_number":"12345","change_url":"https://gerrit.example.com/12345","event_type":"patchset-created","patchset_number":"3","patchset_revision":"abc123...","project":"my-project","refspec":"refs/changes/45/12345/3"}'
```

**Example in GitHub Actions:**
```yaml
- name: Validate Gerrit JSON
  run: |
    curl -o validate-json.sh https://raw.githubusercontent.com/org/repo/main/examples/validate-json.sh
    chmod +x validate-json.sh
    ./validate-json.sh '${{ inputs.gerrit_json }}'
```

### Python Script (validate-json.py)

Pure Python validation with detailed error messages.

**Requirements:**
- Python 3.6+

**Usage:**
```bash
./validate-json.py '{"branch":"master","change_id":"I123...","change_number":"12345","change_url":"https://gerrit.example.com/12345","event_type":"patchset-created","patchset_number":"3","patchset_revision":"abc123...","project":"my-project","refspec":"refs/changes/45/12345/3"}'
```

**Example in GitHub Actions:**
```yaml
- name: Validate Gerrit JSON
  run: |
    curl -o validate-json.py https://raw.githubusercontent.com/org/repo/main/examples/validate-json.py
    python3 validate-json.py '${{ inputs.gerrit_json }}'
```

## Accessing Fields in Workflows

### Using jq in Shell

```bash
# Parse individual fields
BRANCH=$(echo '${{ inputs.gerrit_json }}' | jq -r '.branch')
CHANGE_NUMBER=$(echo '${{ inputs.gerrit_json }}' | jq -r '.change_number')
EVENT_TYPE=$(echo '${{ inputs.gerrit_json }}' | jq -r '.event_type')

echo "Processing change $CHANGE_NUMBER on branch $BRANCH"
```

### Using Python

```python
import json
import os

gerrit_data = json.loads(os.environ['GERRIT_JSON'])

branch = gerrit_data['branch']
change_number = gerrit_data['change_number']
event_type = gerrit_data['event_type']

print(f"Processing change {change_number} on branch {branch}")
```

### In GitHub Actions Steps

```yaml
- name: Parse Gerrit data
  id: parse
  run: |
    echo "branch=$(echo '${{ inputs.gerrit_json }}' | jq -r '.branch')" >> $GITHUB_OUTPUT
    echo "change_number=$(echo '${{ inputs.gerrit_json }}' | jq -r '.change_number')" >> $GITHUB_OUTPUT

- name: Use parsed data
  run: |
    echo "Branch: ${{ steps.parse.outputs.branch }}"
    echo "Change: ${{ steps.parse.outputs.change_number }}"
```

## Complete Workflow Example

```yaml
name: Gerrit Verify
on:
  workflow_dispatch:
    inputs:
      gerrit_json:
        description: 'Gerrit event data as JSON'
        required: true
        type: string
      # Legacy individual fields still available during transition
      GERRIT_BRANCH:
        description: 'Branch'
        required: true
        type: string
      GERRIT_CHANGE_NUMBER:
        description: 'Change number'
        required: true
        type: string

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - name: Validate Gerrit JSON
        run: |
          # Basic validation
          echo '${{ inputs.gerrit_json }}' | jq empty
          
      - name: Parse event data
        id: gerrit
        run: |
          echo "branch=$(echo '${{ inputs.gerrit_json }}' | jq -r '.branch')" >> $GITHUB_OUTPUT
          echo "change_number=$(echo '${{ inputs.gerrit_json }}' | jq -r '.change_number')" >> $GITHUB_OUTPUT
          echo "event_type=$(echo '${{ inputs.gerrit_json }}' | jq -r '.event_type')" >> $GITHUB_OUTPUT
          echo "refspec=$(echo '${{ inputs.gerrit_json }}' | jq -r '.refspec')" >> $GITHUB_OUTPUT
          
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          ref: ${{ steps.gerrit.outputs.branch }}
          fetch-depth: 0
          
      - name: Fetch change
        run: |
          git fetch origin ${{ steps.gerrit.outputs.refspec }}
          git checkout FETCH_HEAD
          
      - name: Run tests
        run: |
          echo "Testing change ${{ steps.gerrit.outputs.change_number }}"
          # Your test commands here
```

## Migration Notes

During the transition period, both `gerrit_json` and individual `GERRIT_*` variables are available. The `gerrit_json` variable contains the same data as the individual variables, just consolidated into a single JSON object.

**Mapping:**
- `gerrit_json.branch` ↔ `GERRIT_BRANCH`
- `gerrit_json.change_id` ↔ `GERRIT_CHANGE_ID`
- `gerrit_json.change_number` ↔ `GERRIT_CHANGE_NUMBER`
- `gerrit_json.change_url` ↔ `GERRIT_CHANGE_URL`
- `gerrit_json.event_type` ↔ `GERRIT_EVENT_TYPE`
- `gerrit_json.patchset_number` ↔ `GERRIT_PATCHSET_NUMBER`
- `gerrit_json.patchset_revision` ↔ `GERRIT_PATCHSET_REVISION`
- `gerrit_json.project` ↔ `GERRIT_PROJECT`
- `gerrit_json.refspec` ↔ `GERRIT_REFSPEC`
- `gerrit_json.comment` ↔ `GERRIT_COMMENT`

## Testing

You can test the validation scripts with example data:

```bash
# Test patchset-created event
./validate-json.sh '{"branch":"master","change_id":"I1234567890abcdef1234567890abcdef12345678","change_number":"12345","change_url":"https://gerrit.example.com/r/c/test-project/+/12345","event_type":"patchset-created","patchset_number":"3","patchset_revision":"abcdef1234567890abcdef1234567890abcdef12","project":"test-project","refspec":"refs/changes/45/12345/3"}'

# Test comment-added event with comment field
./validate-json.py '{"branch":"main","change_id":"Iabcdef","change_number":"67890","change_url":"https://gerrit.example.com/r/c/test/+/67890","event_type":"comment-added","patchset_number":"1","patchset_revision":"fedcba0987654321fedcba0987654321fedcba09","project":"test","refspec":"refs/changes/90/67890/1","comment":"gha-run test-workflow param1=value1"}'
```

## Support

For issues or questions, please contact the maintainers or file an issue in the project repository.