# GitHub Workflow Input Limit Solution

## Problem: GitHub Actions 10-Input Limit (Historic)

> **Update (December 2025):** GitHub has increased the `workflow_dispatch` input
> limit from 10 to **25 inputs**. See the
> [GitHub changelog announcement](https://github.blog/changelog/2025-12-04-actions-workflow-dispatch-workflows-now-support-25-inputs/)
> for details. The constraint described below is now largely resolved, but the
> architectural patterns documented here remain valid and the background context
> is preserved for reference.

GitHub Actions previously had a hard limit of **10 inputs maximum** for `workflow_dispatch` events. This constraint affected how we could trigger workflows from Gerrit events.

### Standard Gerrit Workflow Inputs

All Gerrit workflows (verify, merge, abandon) use these 9 standard inputs:

1. `GERRIT_BRANCH` - Branch the change is against
2. `GERRIT_CHANGE_ID` - The Change-Id (e.g., I123abc...)
3. `GERRIT_CHANGE_NUMBER` - The numeric change ID
4. `GERRIT_CHANGE_URL` - Full URL to the change
5. `GERRIT_EVENT_TYPE` - Event type (patchset-created, change-merged, change-abandoned)
6. `GERRIT_PATCHSET_NUMBER` - Patchset number
7. `GERRIT_PATCHSET_REVISION` - Git commit SHA
8. `GERRIT_PROJECT` - Gerrit project name
9. `GERRIT_REFSPEC` - Git refspec for fetching

### Why This is a Problem for change-abandoned

The `change-abandoned` Gerrit hook provides additional parameters:

- `--abandoner <name> <email>` - Who abandoned the change
- `--abandoner-username <username>` - Username who abandoned
- `--reason <text>` - Reason for abandonment

Adding these as workflow inputs would exceed the 10-input limit:
- 9 standard inputs
- 3 additional inputs
- **Total: 12 inputs ❌ (exceeds limit)**

## Solution: Fetch Additional Data from Gerrit API

Instead of passing abandoner/reason as workflow inputs, we fetch them from the Gerrit REST API.

### Implementation Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Gerrit Hook: change-abandoned                                │
│    - Receives abandoner, reason from Gerrit                     │
│    - Only passes 9 standard inputs to gerrit_to_platform        │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. gerrit_to_platform Handler                                   │
│    - Creates inputs dict with 9 standard fields only            │
│    - Calls GitHub workflow_dispatch API                         │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. GitHub Workflow: gerrit-abandon.yaml                         │
│    - Receives 9 inputs (within limit)                           │
│    - Passes GERRIT_CHANGE_URL to GitHub2Gerrit                  │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. GitHub2Gerrit Action                                         │
│    - Detects G2G_TARGET_URL = GERRIT_CHANGE_URL                 │
│    - Queries Gerrit REST API: GET /changes/{id}?o=MESSAGES      │
│    - Extracts: status, abandoner, messages, reason              │
│    - Closes GitHub PR with complete information                 │
└─────────────────────────────────────────────────────────────────┘
```

### Code Changes Required

#### 1. gerrit_to_platform: change_abandoned.py

```python
def change_abandoned(
    change: str,
    change_url: str,
    change_owner: str,
    change_owner_username: str,
    project: str,
    branch: str,
    topic: str,
    abandoner: str,  # Received but not passed to workflow
    abandoner_username: str,  # Received but not passed to workflow
    commit: str,
    reason: str,  # Received but not passed to workflow
):
    """
    Handle change-abandoned hook.
    
    Note: abandoner, abandoner_username, and reason are received from
    Gerrit but NOT passed as workflow inputs due to GitHub's 10-input
    limit. GitHub2Gerrit will fetch this information from Gerrit REST API.
    """
    change_id = get_change_id(change)
    change_number = get_change_number(change_url)
    patchset = "1"
    refspec = f"refs/heads/{branch}"
    
    # Only 9 inputs - abandoner/reason fetched from API by GitHub2Gerrit
    inputs = {
        "GERRIT_BRANCH": branch,
        "GERRIT_CHANGE_ID": change_id,
        "GERRIT_CHANGE_NUMBER": change_number,
        "GERRIT_CHANGE_URL": change_url,
        "GERRIT_EVENT_TYPE": "change-abandoned",
        "GERRIT_PATCHSET_NUMBER": patchset,
        "GERRIT_PATCHSET_REVISION": commit,
        "GERRIT_PROJECT": project,
        "GERRIT_REFSPEC": refspec,
    }
    
    find_and_dispatch(project, "abandon", inputs)
```

#### 2. GitHub Workflow: .github/workflows/gerrit-abandon.yaml

```yaml
name: 'Gerrit Abandon Handler'

on:
  workflow_dispatch:
    inputs:
      GERRIT_BRANCH:
        required: true
        type: string
      GERRIT_CHANGE_ID:
        required: true
        type: string
      GERRIT_CHANGE_NUMBER:
        required: true
        type: string
      GERRIT_CHANGE_URL:
        required: true
        type: string
      GERRIT_EVENT_TYPE:
        required: true
        type: string
      GERRIT_PATCHSET_NUMBER:
        required: true
        type: string
      GERRIT_PATCHSET_REVISION:
        required: true
        type: string
      GERRIT_PROJECT:
        required: true
        type: string
      GERRIT_REFSPEC:
        required: true
        type: string
      # Total: 9 inputs (within 10-input limit)
      # GitHub2Gerrit will fetch abandoner/reason from Gerrit API

jobs:
  close-github-pr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      
      - name: 'Close GitHub PR'
        uses: modeseven-lfreleng-actions/github2gerrit-action@sync-updates
        env:
          # GitHub2Gerrit queries Gerrit API for abandoner/reason
          G2G_TARGET_URL: ${{ github.event.inputs.GERRIT_CHANGE_URL }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GERRIT_SSH_PRIVKEY_G2G: ${{ secrets.GERRIT_SSH_PRIVKEY_G2G }}
          GERRIT_KNOWN_HOSTS: ${{ vars.GERRIT_KNOWN_HOSTS }}
          CLOSE_MERGED_PRS: 'true'
```

#### 3. GitHub2Gerrit Enhancement

Enhance `check_gerrit_change_status()` to return full change details:

```python
@dataclass
class GerritChangeDetails:
    """Complete details about a Gerrit change."""
    status: Literal["MERGED", "ABANDONED", "NEW", "UNKNOWN"]
    abandoner: str | None = None
    abandoner_email: str | None = None
    reason: str | None = None
    submitted_by: str | None = None
    submitted_by_email: str | None = None

def get_gerrit_change_details(
    gerrit_change_url: str,
) -> GerritChangeDetails:
    """
    Fetch complete change details from Gerrit REST API.
    
    Queries Gerrit with options:
    - MESSAGES: Get all messages/comments
    - DETAILED_ACCOUNTS: Get full account details
    
    Returns:
        GerritChangeDetails with status, abandoner, reason, etc.
    """
    parsed = extract_change_number_from_url(gerrit_change_url)
    if not parsed:
        return GerritChangeDetails(status="UNKNOWN")
    
    host, change_number = parsed
    
    try:
        client = build_client_for_host(host)
        
        # Query with additional options
        change_data = client.get(
            f"/changes/{change_number}?o=MESSAGES&o=DETAILED_ACCOUNTS"
        )
        
        status = change_data.get("status", "UNKNOWN")
        
        details = GerritChangeDetails(status=status)
        
        # Extract abandoner info if abandoned
        if status == "ABANDONED":
            # Check messages for abandonment event
            messages = change_data.get("messages", [])
            for msg in reversed(messages):  # Most recent first
                if "abandoned this change" in msg.get("message", "").lower():
                    author = msg.get("author", {})
                    details.abandoner = author.get("name")
                    details.abandoner_email = author.get("email")
                    
                    # Extract reason from message text
                    # Format: "Abandoned\n\nReason text here"
                    message_text = msg.get("message", "")
                    if "\n\n" in message_text:
                        details.reason = message_text.split("\n\n", 1)[1].strip()
                    break
        
        # Extract submitter info if merged
        elif status == "MERGED":
            submitter = change_data.get("submitter", {})
            details.submitted_by = submitter.get("name")
            details.submitted_by_email = submitter.get("email")
        
        return details
        
    except Exception as exc:
        log.warning("Failed to fetch Gerrit change details: %s", exc)
        return GerritChangeDetails(status="UNKNOWN")
```

Update `close_pr_with_status()` to use the enhanced details:

```python
def close_pr_with_status(
    pr_url: str,
    gerrit_change_details: GerritChangeDetails,
    ...
):
    if gerrit_change_details.status == "ABANDONED":
        # Build comment with abandoner and reason
        comment_parts = [
            f"This pull request is being closed because the corresponding "
            f"Gerrit change was abandoned.",
            "",
            f"**Change:** {gerrit_change_url}",
        ]
        
        if gerrit_change_details.abandoner:
            comment_parts.append(
                f"**Abandoned by:** {gerrit_change_details.abandoner}"
            )
        
        if gerrit_change_details.reason:
            comment_parts.append("")
            comment_parts.append("**Reason:**")
            comment_parts.append(f"> {gerrit_change_details.reason}")
        
        comment = "\n".join(comment_parts)
```

## Benefits of This Approach

✅ **Stays within GitHub's 10-input limit** - Uses only 9 standard inputs

✅ **No information loss** - All abandoner/reason data still available

✅ **Consistent with other workflows** - All Gerrit workflows use same 9 inputs

✅ **More reliable** - Fetches latest state from Gerrit API (source of truth)

✅ **Handles edge cases** - Works even if hook parameters are missing

✅ **Single source of truth** - Gerrit API is authoritative, not hook parameters

## Alternative: repository_dispatch

> **Note:** With the December 2025 increase to 25 inputs, `repository_dispatch`
> is less likely to be needed. It remains documented here as an option for
> edge cases that exceed even the new limit.

If we need more than 25 inputs in the future, we could use `repository_dispatch` instead:

```yaml
# Instead of workflow_dispatch
on:
  repository_dispatch:
    types: [gerrit-abandon]

jobs:
  close-pr:
    runs-on: ubuntu-latest
    steps:
      - name: Extract inputs
        run: |
          echo "CHANGE_URL=${{ github.event.client_payload.GERRIT_CHANGE_URL }}" >> $GITHUB_ENV
          echo "ABANDONER=${{ github.event.client_payload.GERRIT_ABANDONER }}" >> $GITHUB_ENV
          # ... unlimited fields in client_payload
```

**Pros:**
- No 10-input limit
- Can pass unlimited JSON data

**Cons:**
- Cannot trigger manually from GitHub UI (no "Run workflow" button)
- Different API endpoint in gerrit_to_platform
- Less visibility in Actions UI

**Recommendation:** Stick with `workflow_dispatch` + Gerrit API approach for consistency.
With the 25-input limit (as of December 2025), this is even more viable.

## Testing Checklist

- [ ] Verify workflow accepts exactly 9 inputs
- [ ] Test manual workflow_dispatch from GitHub UI
- [ ] Abandon a Gerrit change and verify workflow triggers
- [ ] Verify GitHub2Gerrit fetches abandoner from Gerrit API
- [ ] Verify GitHub2Gerrit fetches reason from Gerrit API
- [ ] Verify PR closure comment includes abandoner and reason
- [ ] Test with empty/missing reason
- [ ] Test with special characters in reason

## References

- GitHub Actions Input Limits: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_dispatchinputs
- GitHub Changelog — 25-input limit (December 4, 2025): https://github.blog/changelog/2025-12-04-actions-workflow-dispatch-workflows-now-support-25-inputs/
- Gerrit REST API: https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html
- gerrit_to_platform workflows: See existing change-merged and patchset-created handlers