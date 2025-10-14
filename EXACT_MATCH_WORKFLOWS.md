# Exact Workflow Matching

## Problem

By default, `gerrit_to_platform` triggers **ALL** workflows that match the event type filter. This means if you have multiple verify workflows:

- `.github/workflows/gerrit-maven-jdk21-verify.yaml`
- `.github/workflows/gerrit-maven-jdk17-verify.yaml`
- `.github/workflows/gerrit-maven-jdk17-mri-verify.yaml`
- `.github/workflows/gerrit-packer-verify.yaml`
- `.github/workflows/gerrit-shellcheck-verify.yaml`
- `.github/workflows/gerrit-ci-verify.yaml`

When a `patchset-created` event occurs, **all workflows** will be triggered because they all contain "gerrit" + "verify" in their filenames.

## Solution: Exact Match Mode

The `exact_match` configuration option enables precise workflow selection. When enabled, only workflows with the exact pattern `gerrit-<event>.yaml` (or `.yml`) will be triggered.

### Configuration

Add to your `~/.config/gerrit_to_platform/gerrit_to_platform.ini`:

```ini
[workflow]
# Enable exact workflow matching
exact_match = true
```

### Behavior

With `exact_match = true`:

#### ✅ Will trigger:
- `.github/workflows/gerrit-verify.yaml` → for patchset-created events
- `.github/workflows/gerrit-merge.yaml` → for change-merged events
- `.github/workflows/gerrit-verify.yml` → also matches (different extension)

#### ❌ Will NOT trigger:
- `.github/workflows/gerrit-packer-verify.yaml` (has extra text after "gerrit-")
- `.github/workflows/gerrit-shellcheck-verify.yaml` (has extra text)
- `.github/workflows/gerrit-ci-management-verify.yaml` (has extra text)

### Required Workflows

Exact matching also works with required workflows in the organization `.github` repository:

#### ✅ Will match with `exact_match = true`:
- `.github/workflows/gerrit-required-verify.yaml`
- `.github/workflows/gerrit-verify-required.yaml`
- `.github/workflows/gerrit-required-merge.yaml`
- `.github/workflows/gerrit-merge-required.yaml`

## Migration Guide

### Option 1: Use Exact Match (Recommended for New Setup)

1. **Rename your workflows** to follow the exact pattern:
   ```
   .github/workflows/gerrit-packer-verify.yaml
   → .github/workflows/gerrit-verify.yaml
   ```

2. **Enable exact match** in config:
   ```ini
   [workflow]
   exact_match = true
   ```

3. **Consolidate workflows**: If you need multiple jobs, put them in a single workflow with a matrix or multiple jobs:
   ```yaml
   name: Gerrit Verify
   
   jobs:
     packer-validate:
       runs-on: ubuntu-latest
       steps:
         - name: Validate Packer
           # ...
     
     shellcheck:
       runs-on: ubuntu-latest
       steps:
         - name: Run Shellcheck
           # ...
   ```

### Option 2: Keep Substring Matching (Legacy)

Keep `exact_match = false` (or omit the config) to maintain backward compatibility. All matching workflows will continue to trigger.

## Examples

### Example 1: Single Consolidated Workflow

**Config:**
```ini
[workflow]
exact_match = true
```

**Workflow:** `.github/workflows/gerrit-verify.yaml`
```yaml
name: Gerrit Verify

on:
  workflow_dispatch:
    inputs:
      GERRIT_BRANCH:
        required: true
        type: string
      # ... other GERRIT inputs

jobs:
  # All verification jobs in one workflow
  packer-validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check for packer changes
        uses: dorny/paths-filter@v3
        id: packer-changes
        with:
          filters: |
            src:
              - 'packer/**'
      - name: Validate Packer
        if: steps.packer-changes.outputs.src == 'true'
        uses: askb/releng-packer-action@main
        with:
          mode: validate

  shellcheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check for shell scripts
        uses: dorny/paths-filter@v3
        id: shell-changes
        with:
          filters: |
            src:
              - '**/*.sh'
      - name: Run Shellcheck
        if: steps.shell-changes.outputs.src == 'true'
        run: shellcheck **/*.sh
```

**Result:** Only ONE workflow is triggered for patchset-created events.

### Example 2: Separate Workflows (Legacy Behavior)

**Config:**
```ini
[workflow]
exact_match = false  # or omit this section
```

**Workflows:**
- `.github/workflows/gerrit-packer-verify.yaml`
- `.github/workflows/gerrit-shellcheck-verify.yaml`

**Result:** BOTH workflows are triggered for patchset-created events.

## Testing Your Configuration

### Test Exact Match

1. Create a workflow: `.github/workflows/gerrit-verify.yaml`
2. Create another: `.github/workflows/gerrit-packer-verify.yaml`
3. Enable exact_match in config
4. Create a Gerrit patchset
5. Verify only `gerrit-verify.yaml` is triggered

### Test Substring Match (Default)

1. Keep the same workflows
2. Set `exact_match = false` or remove the config
3. Create a Gerrit patchset
4. Verify BOTH workflows are triggered

## Troubleshooting

### No workflows are being triggered

**Cause:** Workflow filename doesn't match the exact pattern.

**Fix:**
- Rename workflow to `gerrit-verify.yaml` or `gerrit-merge.yaml`
- OR disable exact_match: `exact_match = false`

### Multiple workflows still triggering with exact_match = true

**Cause:** Configuration not being read correctly.

**Fix:**
- Verify config file location: `~/.config/gerrit_to_platform/gerrit_to_platform.ini`
- Check config syntax (use `[workflow]` section header)
- Restart gerrit_to_platform service/hooks

### Want different workflows for different changes

**Use case:** Trigger packer workflow only for packer changes, shellcheck only for shell scripts.

**Solution:** Use a single workflow with conditional jobs and path filters (see Example 1 above).

## Best Practices

1. **Use exact_match = true** for new deployments to avoid confusion
2. **Consolidate related checks** into a single workflow with multiple jobs
3. **Use path filters** (`dorny/paths-filter@v3`) to conditionally run jobs
4. **Use matrix builds** when you need to run the same job with different parameters
5. **Keep workflow names descriptive** even with exact matching

## Migration Checklist

- [ ] Audit existing workflow files
- [ ] Decide on exact_match vs substring matching
- [ ] Rename workflows to follow exact pattern (if using exact_match)
- [ ] Consolidate related checks into single workflows
- [ ] Add path filters for conditional execution
- [ ] Update configuration file
- [ ] Test with sample Gerrit change
- [ ] Monitor workflow triggers for a few days
- [ ] Document your workflow naming convention

## See Also

- [GERRIT_WORKFLOW_SELECTION.md](GERRIT_WORKFLOW_SELECTION.md) - Original workflow selection documentation
- [gerrit_to_platform README](README.rst) - Main documentation
