# Changelog - gerrit_json Implementation

## 2024-12-01 - Added gerrit_json Consolidated Variable

### Overview
Added a new `gerrit_json` input variable that consolidates all individual `GERRIT_*` variables into a single JSON object. This change addresses the limitation on the number of inputs that can be passed to `workflow_dispatch` events in GitHub Actions.

### Changes Made

#### 1. Core Implementation (`src/gerrit_to_platform/helpers.py`)
- Added `import json` to support JSON serialization
- Added new `build_gerrit_json()` function that converts `GERRIT_*` inputs to a consolidated JSON object
- Modified `find_and_dispatch()` to automatically add `gerrit_json` to inputs before dispatching workflows
- JSON uses snake_case keys (e.g., `change_id` instead of `GERRIT_CHANGE_ID`)
- JSON is compact (no spaces) to minimize size

#### 2. Validation Scripts (`examples/`)
Created two validation scripts for downstream consumers:

**`examples/validate-json.sh`** (Bash/jq)
- Validates JSON structure using `jq`
- Checks all required fields are present
- Validates `event_type` is one of: `patchset-created`, `change-merged`, `comment-added`
- Confirms all values are strings
- Provides detailed error messages

**`examples/validate-json.py`** (Python)
- Pure Python validation (no external dependencies)
- Same validation logic as shell script
- Better error messages and warnings
- Can be used in Python-based workflows

#### 3. Documentation (`examples/README.md`)
Comprehensive documentation including:
- JSON schema definition
- Field descriptions and requirements
- Usage examples for both validation scripts
- GitHub Actions workflow integration examples
- Migration guide showing mapping between old and new formats
- Testing examples

#### 4. Tests (`tests/test_helpers.py`)
Added three new test functions:
- `test_build_gerrit_json()` - Tests basic JSON generation with required fields
- `test_build_gerrit_json_with_comment()` - Tests optional `comment` field inclusion
- `test_build_gerrit_json_is_compact()` - Verifies JSON is compact (no spaces)
- Modified `test_find_and_dispatch()` to verify `gerrit_json` is added to inputs

### JSON Schema

```json
{
  "branch": "string (required)",
  "change_id": "string (required)",
  "change_number": "string (required)",
  "change_url": "string (required)",
  "event_type": "string (required, enum: patchset-created|change-merged|comment-added)",
  "patchset_number": "string (required)",
  "patchset_revision": "string (required)",
  "project": "string (required)",
  "refspec": "string (required)",
  "comment": "string (optional, only for comment-added events)"
}
```

### Field Mapping

| gerrit_json Key | Original GERRIT_* Variable |
|----------------|---------------------------|
| `branch` | `GERRIT_BRANCH` |
| `change_id` | `GERRIT_CHANGE_ID` |
| `change_number` | `GERRIT_CHANGE_NUMBER` |
| `change_url` | `GERRIT_CHANGE_URL` |
| `event_type` | `GERRIT_EVENT_TYPE` |
| `patchset_number` | `GERRIT_PATCHSET_NUMBER` |
| `patchset_revision` | `GERRIT_PATCHSET_REVISION` |
| `project` | `GERRIT_PROJECT` |
| `refspec` | `GERRIT_REFSPEC` |
| `comment` | `GERRIT_COMMENT` |

### Backward Compatibility

**Important:** This is a **parallel implementation**. Both formats are now available:
- Individual `GERRIT_*` variables continue to work as before
- New `gerrit_json` variable is added alongside them
- Downstream workflows can migrate at their own pace
- No breaking changes to existing workflows

### Example Usage

#### In GitHub Actions Workflow
```yaml
on:
  workflow_dispatch:
    inputs:
      gerrit_json:
        description: 'Gerrit event data as JSON'
        required: true
        type: string

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - name: Validate Gerrit JSON
        run: echo '${{ inputs.gerrit_json }}' | jq empty
        
      - name: Extract fields
        id: gerrit
        run: |
          echo "branch=$(echo '${{ inputs.gerrit_json }}' | jq -r '.branch')" >> $GITHUB_OUTPUT
          echo "change_number=$(echo '${{ inputs.gerrit_json }}' | jq -r '.change_number')" >> $GITHUB_OUTPUT
```

#### Example JSON Output
```json
{"branch":"master","change_id":"I1234567890abcdef","change_number":"12345","change_url":"https://gerrit.example.com/12345","event_type":"patchset-created","patchset_number":"3","patchset_revision":"abcdef123456","project":"test-project","refspec":"refs/changes/45/12345/3"}
```

### Benefits

1. **Reduced Input Count**: Single variable instead of 9-10 individual variables
2. **Easier to Pass**: JSON is easier to forward between workflows
3. **Extensible**: Easy to add new fields without workflow signature changes
4. **Validated**: Validation scripts ensure data integrity
5. **Backward Compatible**: Existing workflows continue to work

### Testing

All tests pass:
- 3 new tests for `build_gerrit_json()` functionality
- All existing tests continue to pass
- Integration tests verify `gerrit_json` is properly added to dispatched workflows

### Files Changed

```
gerrit_to_platform/
├── examples/
│   ├── CHANGELOG.md (this file)
│   ├── README.md (new)
│   ├── validate-json.sh (new, executable)
│   └── validate-json.py (new, executable)
├── src/gerrit_to_platform/
│   └── helpers.py (modified)
└── tests/
    └── test_helpers.py (modified)
```

### Next Steps

1. Deploy updated `gerrit_to_platform` to production
2. Update downstream workflows to use `gerrit_json` where beneficial
3. Monitor for any issues
4. Eventually deprecate individual `GERRIT_*` variables (future release)