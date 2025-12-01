#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2024 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""
Validate gerrit_json against the schema.

Usage: validate-json.py <gerrit_json_string>

Example:
    ./validate-json.py '{"branch":"master","change_id":"I123...","change_number":"12345",...}'
"""

import json
import sys
from typing import Any, Dict


REQUIRED_FIELDS = [
    "branch",
    "change_id",
    "change_number",
    "change_url",
    "event_type",
    "patchset_number",
    "patchset_revision",
    "project",
    "refspec",
]

VALID_EVENT_TYPES = ["patchset-created", "change-merged", "comment-added"]

OPTIONAL_FIELDS = ["comment"]


def validate_gerrit_json(gerrit_json_str: str) -> bool:
    """
    Validate gerrit_json against schema.

    Args:
        gerrit_json_str: JSON string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    # Parse JSON
    try:
        data = json.loads(gerrit_json_str)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        return False

    if not isinstance(data, dict):
        print("ERROR: JSON must be an object")
        return False

    # Check required fields
    print("Validating required fields...")
    for field in REQUIRED_FIELDS:
        if field not in data:
            print(f"ERROR: Missing required field: {field}")
            return False
        print(f"  ✓ {field}")

    # Validate event_type
    print("\nValidating event_type...")
    if data["event_type"] not in VALID_EVENT_TYPES:
        print(f"ERROR: Invalid event_type: {data['event_type']}")
        print(f"Must be one of: {', '.join(VALID_EVENT_TYPES)}")
        return False
    print(f"  ✓ event_type: {data['event_type']}")

    # Validate all values are strings
    print("\nValidating field types...")
    for key, value in data.items():
        if not isinstance(value, str):
            print(
                f"ERROR: Field '{key}' must be a string, got {type(value).__name__}"
            )
            return False
    print("  ✓ All fields are strings")

    # Check for unknown fields (warn only)
    known_fields = set(REQUIRED_FIELDS + OPTIONAL_FIELDS)
    unknown_fields = set(data.keys()) - known_fields
    if unknown_fields:
        print(f"\nWarning: Unknown fields present: {', '.join(unknown_fields)}")

    print("\n✓ gerrit_json is valid")
    print("\nPretty-printed JSON:")
    print(json.dumps(data, indent=2))
    return True


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <gerrit_json_string>")
        print("\nExample:")
        print(
            f'  {sys.argv[0]} \'{{"branch":"master","change_id":"I123..."}}\''
        )
        return 1

    if not validate_gerrit_json(sys.argv[1]):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())