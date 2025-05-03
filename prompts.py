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
        "Each element must have the following structure: "
        "{"
        "  'file': string (the file name), "
        "  'line': integer (the line number of the change, or 1 if undetermined), "
        "  'comments': array of strings (specific feedback or issues for the change)"
        "}. "
        "If no issues are found for a file, include an element with an empty 'comments' array. "
        "If the diff is empty or missing, return an empty array. "
        "Ensure the response is valid JSON."
    )

    if deep:
        return (
            "Review the provided code diffs and identify issues, including bugs, style improvements, and suggestions for better maintainability. "
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