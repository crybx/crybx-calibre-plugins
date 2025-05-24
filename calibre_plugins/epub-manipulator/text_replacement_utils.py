#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility functions for text replacement in EPUB files.
Provides pattern loading, validation, and application functionality.
"""

import re
import json

from pattern_definitions import get_patterns



def load_replacement_patterns(pattern_file=None, verbose=False):
    """
    Load replacement patterns from Python definitions or JSON files.

    Args:
        pattern_file: Path to JSON file with patterns to optionally add
        verbose: Whether to output detailed information

    Returns:
        Dictionary of replacement patterns
    """


    # load patterns from Python definitions
    patterns = get_patterns()

    # load additional patterns from json file
    if pattern_file is not None:
        try:
            with open(pattern_file, 'r', encoding='utf-8') as f:
                additional_patterns = json.load(f)
            patterns.update(additional_patterns)

        except Exception as e:
            pass

    return patterns


def validate_replacement_patterns(patterns):
    """
    Validate a set of replacement patterns for potential issues.

    Args:
        patterns: List of replacement pattern dictionaries

    Returns:
        List of warnings or issues
    """
    warnings = []
    processed_patterns = {}

    for i, pattern_dict in enumerate(patterns):
        for find, replace in pattern_dict.items():
            # Check for empty patterns
            if not find:
                warnings.append(f"Pattern #{i + 1} has an empty 'find' string")

            # Check for duplicates
            if find in processed_patterns:
                if processed_patterns[find] != replace:
                    warnings.append(
                        f"Pattern '{find}' has conflicting replacements: '{processed_patterns[find]}' and '{replace}'")
                else:
                    warnings.append(f"Pattern '{find}' -> '{replace}' is duplicated")

            processed_patterns[find] = replace

            # Check for patterns that might cause issues
            if find in replace:
                warnings.append(
                    f"Pattern '{find}' -> '{replace}' contains itself in the replacement, which might cause recursion")

    return warnings


def apply_replacements_to_content(content, patterns, verbose=False, all_patterns=None, visited_patterns=None):
    """
    Apply replacement patterns to content. Handles both simple string
    replacements and regex-based replacements.

    Args:
        content: HTML content as string
        patterns: List of replacement pattern dictionaries
        verbose: Whether to output verbose logging
        all_patterns: Dictionary containing all available pattern groups (used for pattern inclusion)
        visited_patterns: Set of pattern names that have already been processed (prevents infinite recursion)

    Returns:
        Modified content as string, replacement count
    """

    if not content:
        return content, 0

    # Initialize tracking sets for pattern inclusion/recursion prevention
    if visited_patterns is None:
        visited_patterns = set()

    modified_content = content
    replacement_count = 0

    # Process pattern dictionaries
    for pattern_dict in patterns:
        # Check if this is a pattern inclusion directive
        if isinstance(pattern_dict, dict) and "include_patterns" in pattern_dict:
            # Handle pattern group inclusion
            if all_patterns is None:
                continue

            # Get list of patterns to include
            included_pattern_names = pattern_dict["include_patterns"]
            if not isinstance(included_pattern_names, list):
                included_pattern_names = [included_pattern_names]  # Convert single string to list

            # Process each included pattern group
            for pattern_name in included_pattern_names:
                # Skip if we've already processed this pattern (prevents infinite recursion)
                if pattern_name in visited_patterns:
                    continue

                # Get the patterns from the included group
                if pattern_name in all_patterns:
                    # Mark this pattern as visited
                    visited_patterns.add(pattern_name)

                    # Recursively apply the included patterns
                    sub_content, sub_count = apply_replacements_to_content(
                        modified_content,
                        all_patterns[pattern_name],
                        verbose,
                        all_patterns,
                        visited_patterns
                    )
                    modified_content = sub_content
                    replacement_count += sub_count

        # Check if this is a regex pattern
        elif isinstance(pattern_dict, dict) and "regex" in pattern_dict and "replace" in pattern_dict:
            # This is a regex pattern
            try:
                regex = pattern_dict["regex"]
                replace = pattern_dict["replace"]

                # Check if this is a case transformation
                if "transform" in pattern_dict and "uppercase" in pattern_dict["transform"].lower():
                    # Count matches before replacement to track the number of replacements
                    matches = len(re.findall(regex, modified_content))
                    replacement_count += matches

                    def case_transform(match):
                        groups = []
                        # Safely get groups, handling None values
                        for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                            group_value = match.group(i)
                            groups.append("" if group_value is None else group_value)

                        # Apply uppercase to the specified group
                        transform_group = pattern_dict.get("transform_group", len(groups)) - 1
                        if 0 <= transform_group < len(groups):
                            groups[transform_group] = groups[transform_group].upper()

                        # Build the replacement string
                        result = replace
                        for i in range(len(groups)):
                            group_ref = f"\\{i + 1}"
                            result = result.replace(group_ref, groups[i])
                        return result

                    # Apply the replacement with case transformation
                    modified_content = re.sub(regex, case_transform, modified_content)
                else:
                    # Count matches before replacement
                    matches = len(re.findall(regex, modified_content))
                    replacement_count += matches

                    # Apply regex replacement
                    modified_content = re.sub(regex, replace, modified_content)


            except re.error as e:
                pass
        else:
            # This is a simple string replacement
            for find, replace in pattern_dict.items():
                # Count occurrences before replacement
                count_before = modified_content.count(find)
                if count_before > 0:
                    # Replace the pattern
                    modified_content = modified_content.replace(find, replace)
                    # Update the replacement count
                    replacement_count += count_before

    return modified_content, replacement_count
