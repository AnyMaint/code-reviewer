def get_prompt(deep: bool = False) -> str:
    """
    Returns the prompt for the given mode and deep flag, instructing LLM to return JSON output.

    Args:
        mode: The mode ('issues', 'comments').
        deep: Whether deep mode is enabled (verbose feedback).

    Returns:
        The prompt to use for the LLM.
    """
    base_json_schema = (
        "Return a JSON array where each element represents feedback for a file's diff. "
        "Each element must have the following structure: {\n"        
        " 'file'               - string: the file path or name\n"
        " 'line':  integer (the line number of issue in the new file from 'Line in new file', or old file from 'Line in old file' for deletions)",
        " 'comments'           - array of strings: detailed feedback items\n"
        " 'bugCount'           - integer: total number of bugs detected in this diff\n"
        " 'smellCount'         - integer: total number of code-smell issues found\n"
        " 'optimizationCount'  - integer: total number of optimization suggestions\n"
        " 'logicalErrors'      - integer: total number of logical errors\n"
        " 'performanceIssues'  - integer: total number of performance issues\n"
        "}\n"
        "Rules:\n"
        "  1. Include one object per file, even if all counts are zero and comments is empty.\n"
        "  2. If a file has no issues, set bugCount, smellCount, optimizationCount, logicalErrors, performanceIssues to 0 and comments to [].\n"
        "  3. If the entire diff is empty or missing, return an empty array.\n"
        "  4. Output must be valid, parsable JSON (no trailing commas, use double-quotes for keys/strings).\n"
    )

    if deep:
        return (
            "Review the provided code diffs and identify issues, including bugs, smells, style improvements, and suggestions for better maintainability. "
            "For each file, provide detailed feedback on problems directly related to the changes, such as logical errors, performance issues, or maintainability concerns. "
            "Use the PR description to understand the intent and do not flag issues if the PR description explains the reasoning behind a change, unless the change introduces a clear bug. "
            f"{base_json_schema} "
            "For each file, include specific issues or suggestions in the 'comments' array, referencing the modified lines."
        )
    else:
        return (
            "Review the provided code diffs and identify critical bugs directly visible in the modified lines, such as syntax errors, null-pointer exceptions, or logical errors. "
            "Use the PR description to understand the intent and do not flag issues if the PR description explains the reasoning behind a change, unless the change introduces a clear bug. "
            "Do not provide general suggestions or speculative concerns. "
            f"{base_json_schema} "
            "For each file, include only critical bugs in the 'comments' array, referencing the modified lines."
        )