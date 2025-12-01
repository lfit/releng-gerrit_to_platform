# GitHub Actions Workflows for gerrit_json Testing

This directory contains comprehensive test workflows for the `gerrit_json` consolidated variable feature.

## Overview

The `gerrit_json` feature consolidates all individual `GERRIT_*` variables into a single JSON object, addressing the workflow_dispatch input limit of 10 variables.

## Workflows

### 1. `testing.yaml` - Automated Test Suite 🧪

**Trigger:** Automatically runs on pull requests and pushes to main

**Purpose:** Comprehensive automated testing of the gerrit_json feature

**Test Coverage:**
- ✅ JSON generation from GERRIT_* variables
- ✅ Shell validation script (validate-json.sh)
- ✅ Python validation script (validate-json.py)
- ✅ Downstream workflow consumption
- ✅ All three event types (patchset-created, change-merged, comment-added)
- ✅ Optional comment field handling
- ✅ Invalid input rejection
- ✅ Field type validation
- ✅ Event type enumeration validation

**Jobs:**
1. `test-json-generation` - Generates gerrit_json and validates structure
2. `test-shell-validation` - Tests validate-json.sh with valid and invalid data
3. `test-python-validation` - Tests validate-json.py with valid and invalid data
4. `test-downstream-consumer` - Simulates downstream workflow consumption
5. `test-multiple-events` - Tests all three event types in matrix
6. `test-summary` - Aggregates results and provides final summary

**Usage:**
This workflow runs automatically on every PR. No manual intervention needed.

### 2. `downstream-consumer.yaml` - Downstream Consumer Demo 📥

**Trigger:** Manual workflow_dispatch (can be called by other workflows)

**Purpose:** Demonstrates how a downstream workflow would consume gerrit_json

**Features:**
- Receives **all 10 individual GERRIT_* variables** (demonstrating the workflow_dispatch limit)
- Receives **1 consolidated gerrit_json variable**
- Validates gerrit_json with both Shell and Python scripts
- Parses JSON and extracts all fields
- Compares legacy variables with JSON values to ensure consistency
- Demonstrates typical usage patterns

**Required Inputs (10 total - at workflow_dispatch limit!):**
1. `gerrit_json` - Consolidated JSON variable ⭐ NEW
2. `GERRIT_BRANCH` - Branch name
3. `GERRIT_CHANGE_ID` - Gerrit Change-Id
4. `GERRIT_CHANGE_NUMBER` - Change number
5. `GERRIT_CHANGE_URL` - Change URL
6. `GERRIT_EVENT_TYPE` - Event type (patchset-created, change-merged, comment-added)
7. `GERRIT_PATCHSET_NUMBER` - Patchset number
8. `GERRIT_PATCHSET_REVISION` - Git SHA
9. `GERRIT_PROJECT` - Project name
10. `GERRIT_REFSPEC` - Git refspec

Optional Input:
- `GERRIT_COMMENT` - Comment text (for comment-added events)

**Usage:**
Called by `manual-dispatch-test.yaml` or can be triggered manually via Actions tab.

### 3. `manual-dispatch-test.yaml` - Manual Test Dispatcher 🚀

**Trigger:** Manual workflow_dispatch

**Purpose:** Allows manual testing of the complete gerrit_json workflow

**What it does:**
1. Generates realistic test data for a Gerrit event
2. Creates both gerrit_json and individual GERRIT_* variables
3. Validates the generated JSON
4. Dispatches to `downstream-consumer.yaml` with all inputs

**Inputs:**
- `event_type` - Choose event type (patchset-created, change-merged, comment-added)
- `include_comment` - Whether to include GERRIT_COMMENT field
- `comment_text` - Comment text (if include_comment is true)

**Usage:**
1. Go to Actions tab
2. Select "Manual Dispatch Test 🚀" workflow
3. Click "Run workflow"
4. Choose event type and options
5. Click "Run workflow"
6. Watch it dispatch to downstream-consumer workflow

## Testing Strategy

### Automated Testing (PR Validation)

When you create a PR, the `testing.yaml` workflow automatically:
- Generates gerrit_json from test data
- Validates with both Shell and Python scripts
- Tests all event types
- Verifies downstream consumption
- Ensures consistency between legacy and JSON formats

### Manual Testing (Workflow Dispatch Simulation)

To manually test the complete workflow:

1. **Run Manual Dispatch Test:**
   ```bash
   gh workflow run manual-dispatch-test.yaml \
     -f event_type=patchset-created
   ```

2. **Or use the GitHub UI:**
   - Go to Actions → Manual Dispatch Test 🚀
   - Click "Run workflow"
   - Select event type
   - Run and observe

3. **Verify downstream consumer:**
   - Check Actions → Downstream Consumer
   - Verify both formats received correctly
   - Check validation passed
   - Review summary output

## Key Testing Points

### ✅ What We Test

1. **JSON Generation:**
   - All required fields present
   - Optional comment field handled correctly
   - Compact JSON format (no spaces)
   - Valid JSON structure

2. **Validation Scripts:**
   - Shell script validates correctly
   - Python script validates correctly
   - Invalid data is rejected
   - Invalid event_type is rejected
   - Missing fields are detected

3. **Downstream Consumption:**
   - JSON can be parsed with jq
   - All fields extractable
   - Values match legacy variables
   - Typical usage patterns work

4. **Event Types:**
   - patchset-created events
   - change-merged events
   - comment-added events (with optional comment field)

5. **Input Limits:**
   - Demonstrates 10-variable limit with legacy approach
   - Shows single variable with gerrit_json approach
   - Validates both formats simultaneously

### ❌ What We Don't Test (Yet)

These require actual Gerrit integration:
- Real Gerrit hook events
- Actual repository operations
- Real workflow dispatch to external repos
- Integration with gerrit_to_platform CLI

## JSON Schema Reference

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

## Example gerrit_json

```json
{
  "branch": "main",
  "change_id": "I1234567890abcdef1234567890abcdef12345678",
  "change_number": "12345",
  "change_url": "https://gerrit.example.com/r/c/test-project/+/12345",
  "event_type": "patchset-created",
  "patchset_number": "3",
  "patchset_revision": "abcdef1234567890abcdef1234567890abcdef12",
  "project": "test-project",
  "refspec": "refs/changes/45/12345/3"
}
```

## Validation Scripts

Located in `examples/` directory:

- **`validate-json.sh`** - Bash script using jq
  ```bash
  ./examples/validate-json.sh "$GERRIT_JSON"
  ```

- **`validate-json.py`** - Python script (no external dependencies)
  ```bash
  ./examples/validate-json.py "$GERRIT_JSON"
  ```

Both scripts validate:
- Valid JSON structure
- All required fields present
- Valid event_type enum
- All values are strings

## Benefits Summary

### Before (Legacy Approach)
- ❌ 10 individual workflow inputs (at limit!)
- ❌ Complex to pass between workflows
- ❌ Can't add new fields without breaking changes
- ❌ Verbose workflow signatures

### After (gerrit_json Approach)
- ✅ 1 consolidated workflow input
- ✅ Easy to pass between workflows
- ✅ Extensible without breaking changes
- ✅ Clean workflow signatures
- ✅ Leaves 9 input slots for other parameters

## Troubleshooting

### Workflow fails with "invalid JSON"
- Check that gerrit_json is valid JSON: `echo "$GERRIT_JSON" | jq .`
- Verify no extra quotes or escaping issues
- Use validation scripts to diagnose

### Validation scripts fail
- Ensure jq is installed (for Shell script)
- Check Python version >= 3.6 (for Python script)
- Verify all required fields present

### Downstream consumer doesn't receive data
- Check workflow dispatch permissions
- Verify inputs are passed correctly
- Review workflow logs for errors

## Contributing

When adding new features to gerrit_json:

1. Update the schema in `examples/README.md`
2. Update validation scripts
3. Add tests to `testing.yaml`
4. Update this README
5. Test with `manual-dispatch-test.yaml`

## Support

For questions or issues:
- File an issue in the repository
- Check `examples/README.md` for detailed usage
- Review workflow logs in Actions tab