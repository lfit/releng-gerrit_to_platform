#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2024 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
#
# Validates gerrit_json against the schema
#
# Usage: validate-json.sh <gerrit_json_string>
#
# Example:
#   ./validate-json.sh '{"branch":"master","change_id":"I123...","change_number":"12345",...}'
#
##############################################################################

set -e

GERRIT_JSON="$1"

if [ -z "$GERRIT_JSON" ]; then
    echo "Usage: $0 <gerrit_json_string>"
    echo ""
    echo "Example:"
    echo "  $0 '{\"branch\":\"master\",\"change_id\":\"I123...\"}'"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is required but not installed"
    echo "Install with: apt-get install jq (Debian/Ubuntu) or brew install jq (macOS)"
    exit 1
fi

# Validate it's valid JSON
echo "$GERRIT_JSON" | jq empty || {
    echo "ERROR: Invalid JSON"
    exit 1
}

# Check required fields exist
REQUIRED_FIELDS=(
    "branch"
    "change_id"
    "change_number"
    "change_url"
    "event_type"
    "patchset_number"
    "patchset_revision"
    "project"
    "refspec"
)

echo "Validating required fields..."
for field in "${REQUIRED_FIELDS[@]}"; do
    if ! echo "$GERRIT_JSON" | jq -e "has(\"$field\")" > /dev/null; then
        echo "ERROR: Missing required field: $field"
        exit 1
    fi
    echo "  ✓ $field"
done

# Validate event_type is one of the allowed values
echo ""
echo "Validating event_type..."
EVENT_TYPE=$(echo "$GERRIT_JSON" | jq -r '.event_type')
case "$EVENT_TYPE" in
    "patchset-created"|"change-merged"|"comment-added")
        echo "  ✓ event_type: $EVENT_TYPE"
        ;;
    *)
        echo "ERROR: Invalid event_type: $EVENT_TYPE"
        echo "Must be one of: patchset-created, change-merged, comment-added"
        exit 1
        ;;
esac

# Validate all values are strings
echo ""
echo "Validating field types..."
if ! echo "$GERRIT_JSON" | jq -e 'to_entries | all(.value | type == "string")' > /dev/null; then
    echo "ERROR: All values must be strings"
    # Show which fields are not strings
    echo "$GERRIT_JSON" | jq -r 'to_entries | map(select(.value | type != "string")) | .[] | "  Field \(.key) has type \(.value | type)"'
    exit 1
fi
echo "  ✓ All fields are strings"

echo ""
echo "✓ gerrit_json is valid"
echo ""
echo "Pretty-printed JSON:"
echo "$GERRIT_JSON" | jq '.'

exit 0