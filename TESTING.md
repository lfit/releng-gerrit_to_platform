# Testing Checklist for gerrit_json Implementation

This document provides a comprehensive testing checklist for verifying the gerrit_json implementation works correctly.

## Overview

The gerrit_json feature consolidates all `GERRIT_*` variables into a single JSON object, addressing GitHub Actions' workflow_dispatch input limit of 10 variables.

## Pre-PR Testing Checklist

Before submitting your PR, verify the following:

### ✅ Unit Tests

- [ ] All existing unit tests pass
  ```bash
  python -m pytest tests/test_helpers.py -v
  ```

- [ ] New gerrit_json tests pass
  ```bash
  python -m pytest tests/test_helpers.py::test_build_gerrit_json -v
  python -m pytest tests/test_helpers.py::test_build_gerrit_json_with_comment -v
  python -m pytest tests/test_helpers.py::test_build_gerrit_json_is_compact -v
  ```

- [ ] Integration test verifies gerrit_json is added to inputs
  ```bash
  python -m pytest tests/test_helpers.py::test_find_and_dispatch -v
  ```

- [ ] All event handler tests pass
  ```bash
  python -m pytest tests/test_patchset_created.py -v
  python -m pytest tests/test_change_merged.py -v
  python -m pytest tests/test_comment_added.py -v
  ```

### ✅ Validation Scripts

- [ ] Shell validation script is executable
  ```bash
  chmod +x examples/validate-json.sh
  ls -l examples/validate-json.sh
  ```

- [ ] Python validation script is executable
  ```bash
  chmod +x examples/validate-json.py
  ls -l examples/validate-json.py
  ```

- [ ] Shell script validates valid JSON
  ```bash
  ./examples/validate-json.sh '{"branch":"main","change_id":"I123","change_number":"1","change_url":"url","event_type":"patchset-created","patchset_number":"1","patchset_revision":"abc","project":"proj","refspec":"ref"}'
  ```

- [ ] Shell script rejects invalid JSON
  ```bash
  ./examples/validate-json.sh '{"branch":"main"}' && echo "FAIL: Should have rejected" || echo "PASS: Correctly rejected"
  ```

- [ ] Python script validates valid JSON
  ```bash
  ./examples/validate-json.py '{"branch":"main","change_id":"I123","change_number":"1","change_url":"url","event_type":"patchset-created","patchset_number":"1","patchset_revision":"abc","project":"proj","refspec":"ref"}'
  ```

- [ ] Python script rejects invalid event_type
  ```bash
  ./examples/validate-json.py '{"branch":"main","change_id":"I123","change_number":"1","change_url":"url","event_type":"invalid","patchset_number":"1","patchset_revision":"abc","project":"proj","refspec":"ref"}' && echo "FAIL" || echo "PASS"
  ```

### ✅ JSON Generation

- [ ] Generate JSON for patchset-created event
  ```bash
  python -c "
  from gerrit_to_platform.helpers import build_gerrit_json
  import json
  inputs = {
      'GERRIT_BRANCH': 'main',
      'GERRIT_CHANGE_ID': 'I123',
      'GERRIT_CHANGE_NUMBER': '1',
      'GERRIT_CHANGE_URL': 'https://gerrit.test/1',
      'GERRIT_EVENT_TYPE': 'patchset-created',
      'GERRIT_PATCHSET_NUMBER': '1',
      'GERRIT_PATCHSET_REVISION': 'abc123',
      'GERRIT_PROJECT': 'test',
      'GERRIT_REFSPEC': 'refs/changes/01/1/1'
  }
  result = build_gerrit_json(inputs)
  print(json.dumps(json.loads(result), indent=2))
  "
  ```

- [ ] Generate JSON for change-merged event
  ```bash
  python -c "
  from gerrit_to_platform.helpers import build_gerrit_json
  import json
  inputs = {
      'GERRIT_BRANCH': 'main',
      'GERRIT_CHANGE_ID': 'I123',
      'GERRIT_CHANGE_NUMBER': '1',
      'GERRIT_CHANGE_URL': 'https://gerrit.test/1',
      'GERRIT_EVENT_TYPE': 'change-merged',
      'GERRIT_PATCHSET_NUMBER': '1',
      'GERRIT_PATCHSET_REVISION': 'abc123',
      'GERRIT_PROJECT': 'test',
      'GERRIT_REFSPEC': 'refs/heads/main'
  }
  result = build_gerrit_json(inputs)
  print(json.dumps(json.loads(result), indent=2))
  "
  ```

- [ ] Generate JSON for comment-added event with comment
  ```bash
  python -c "
  from gerrit_to_platform.helpers import build_gerrit_json
  import json
  inputs = {
      'GERRIT_BRANCH': 'main',
      'GERRIT_CHANGE_ID': 'I123',
      'GERRIT_CHANGE_NUMBER': '1',
      'GERRIT_CHANGE_URL': 'https://gerrit.test/1',
      'GERRIT_EVENT_TYPE': 'comment-added',
      'GERRIT_PATCHSET_NUMBER': '1',
      'GERRIT_PATCHSET_REVISION': 'abc123',
      'GERRIT_PROJECT': 'test',
      'GERRIT_REFSPEC': 'refs/changes/01/1/1',
      'GERRIT_COMMENT': 'gha-run test-workflow'
  }
  result = build_gerrit_json(inputs)
  print(json.dumps(json.loads(result), indent=2))
  "
  ```

- [ ] Verify JSON is compact (no spaces)
  ```bash
  python -c "
  from gerrit_to_platform.helpers import build_gerrit_json
  inputs = {
      'GERRIT_BRANCH': 'main',
      'GERRIT_CHANGE_ID': 'I123',
      'GERRIT_CHANGE_NUMBER': '1',
      'GERRIT_CHANGE_URL': 'url',
      'GERRIT_EVENT_TYPE': 'patchset-created',
      'GERRIT_PATCHSET_NUMBER': '1',
      'GERRIT_PATCHSET_REVISION': 'abc',
      'GERRIT_PROJECT': 'proj',
      'GERRIT_REFSPEC': 'ref'
  }
  result = build_gerrit_json(inputs)
  if ': ' in result or ', ' in result:
      print('FAIL: JSON not compact')
      exit(1)
  else:
      print('PASS: JSON is compact')
  "
  ```

### ✅ Documentation

- [ ] `examples/README.md` exists and is complete
- [ ] `examples/CHANGELOG.md` documents all changes
- [ ] `examples/validate-json.sh` has proper license header
- [ ] `examples/validate-json.py` has proper license header
- [ ] `examples/example-workflow.yml` demonstrates usage
- [ ] `.github/workflows/README.md` explains test workflows

### ✅ Backward Compatibility

- [ ] All existing GERRIT_* variables still work
- [ ] No changes to event handler function signatures
- [ ] Legacy workflows can continue using individual variables
- [ ] Both formats can coexist during transition

## PR Testing Checklist

When you create a PR, GitHub Actions will automatically run tests:

### ✅ Automated CI Tests (testing.yaml)

The PR will trigger `.github/workflows/testing.yaml` which tests:

- [ ] JSON generation from GERRIT_* variables
- [ ] Shell validation script with valid data
- [ ] Shell validation script rejects invalid data
- [ ] Python validation script with valid data
- [ ] Python validation script rejects invalid data
- [ ] Downstream workflow consumption
- [ ] All three event types in matrix
- [ ] Optional comment field handling
- [ ] Test summary shows all tests passed

**Expected Result:** All jobs in testing.yaml should be green ✅

### ✅ Manual Testing (Optional but Recommended)

After PR is created, manually test the workflow dispatch:

1. [ ] Go to Actions tab in your PR branch
2. [ ] Run "Manual Dispatch Test 🚀" workflow
   - Select event type: patchset-created
   - Click "Run workflow"
3. [ ] Verify it dispatches to downstream-consumer
4. [ ] Check downstream-consumer workflow runs successfully
5. [ ] Review job summaries show correct data
6. [ ] Repeat for change-merged event type
7. [ ] Repeat for comment-added with comment

## Post-PR Testing Checklist

After PR is merged to main:

### ✅ Integration Testing

- [ ] Clone/pull latest main branch
- [ ] Install package: `pip install -e .`
- [ ] Run full test suite: `python -m pytest tests/ -v`
- [ ] Verify all tests pass

### ✅ Workflow Testing

- [ ] Check Actions tab shows testing.yaml ran on main
- [ ] Verify all jobs passed
- [ ] Review step summaries for any warnings

### ✅ Documentation Review

- [ ] Read through examples/README.md
- [ ] Try following examples in examples/README.md
- [ ] Verify validation scripts work as documented

## Known Limitations

These are expected and don't need fixing in this PR:

- ❌ No real Gerrit integration (would require Gerrit server)
- ❌ No actual repository dispatch to external repos (requires setup)
- ❌ Can't test real webhook events (requires Gerrit hooks)
- ⚠️ Some cooldown tests may fail (pre-existing issue, not related to gerrit_json)

## Testing the 10-Variable Limit

The downstream-consumer workflow demonstrates the workflow_dispatch limit:

### Current State (Without gerrit_json)
```yaml
inputs:
  GERRIT_BRANCH: {required: true}
  GERRIT_CHANGE_ID: {required: true}
  GERRIT_CHANGE_NUMBER: {required: true}
  GERRIT_CHANGE_URL: {required: true}
  GERRIT_EVENT_TYPE: {required: true}
  GERRIT_PATCHSET_NUMBER: {required: true}
  GERRIT_PATCHSET_REVISION: {required: true}
  GERRIT_PROJECT: {required: true}
  GERRIT_REFSPEC: {required: true}
  GERRIT_COMMENT: {required: false}
```
**Count: 10 inputs (at limit!)**

### New State (With gerrit_json)
```yaml
inputs:
  gerrit_json: {required: true}
  # 9 more input slots available for other parameters!
```
**Count: 1 input (9 slots free!)**

## Success Criteria

The PR is ready to merge when:

1. ✅ All automated tests pass
2. ✅ Manual dispatch test completes successfully
3. ✅ Validation scripts work correctly
4. ✅ Documentation is complete and accurate
5. ✅ Code review approved
6. ✅ No regression in existing functionality
7. ✅ Both legacy and JSON formats work together

## Quick Test Command Reference

```bash
# Install package
pip install -e .

# Run all tests
python -m pytest tests/ -v

# Run only gerrit_json tests
python -m pytest tests/test_helpers.py -k gerrit_json -v

# Test validation scripts
./examples/validate-json.sh '{"branch":"main","change_id":"I123","change_number":"1","change_url":"url","event_type":"patchset-created","patchset_number":"1","patchset_revision":"abc","project":"proj","refspec":"ref"}'

./examples/validate-json.py '{"branch":"main","change_id":"I123","change_number":"1","change_url":"url","event_type":"patchset-created","patchset_number":"1","patchset_revision":"abc","project":"proj","refspec":"ref"}'

# Generate test JSON
python -c "from gerrit_to_platform.helpers import build_gerrit_json; print(build_gerrit_json({'GERRIT_BRANCH':'main','GERRIT_CHANGE_ID':'I123','GERRIT_CHANGE_NUMBER':'1','GERRIT_CHANGE_URL':'url','GERRIT_EVENT_TYPE':'patchset-created','GERRIT_PATCHSET_NUMBER':'1','GERRIT_PATCHSET_REVISION':'abc','GERRIT_PROJECT':'proj','GERRIT_REFSPEC':'ref'}))"
```

## Questions or Issues?

If you encounter any issues during testing:

1. Check the workflow logs in Actions tab
2. Review the examples/README.md for detailed usage
3. Verify jq is installed for Shell validation
4. Ensure Python 3.6+ is available
5. Check that JSON is properly escaped in workflow YAML

## Summary

This implementation provides:
- ✅ Consolidated gerrit_json variable (1 input instead of 10)
- ✅ Backward compatible (both formats work)
- ✅ Validated (both Shell and Python scripts)
- ✅ Tested (comprehensive GitHub Actions workflows)
- ✅ Documented (extensive examples and guides)
- ✅ Extensible (easy to add new fields in future)