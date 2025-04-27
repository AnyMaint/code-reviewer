# prompts.py

def get_prompt(mode, deep=False):
    """
    Returns the prompt for the given mode and deep flag.

    Args:
        mode (str): The mode ('general', 'issues', 'comments').
        deep (bool): Whether deep mode is enabled (verbose feedback).

    Returns:
        str: The prompt to use for the LLM.
    """
    if mode == "general":
        return (
            "Review the provided pull request details, including the PR title, description, and code diffs. "
            "Provide a high-level summary of the changes, explaining their purpose and overall impact. "
            "Use the PR description to understand the intent of the changes, but focus on summarizing the diffs."
        )

    # Base prompt for issues and comments modes
    if deep:
        return (
                "Review the provided code diff and identify issues, including bugs, style improvements, and suggestions for better maintainability. "
                "Provide detailed feedback on problems directly related to the changes, such as logical errors, performance issues, or maintainability concerns. "
                "Use the PR description to understand the intent and implications of the changes, and do not flag issues as bugs if the PR description explains the reasoning behind a change "
                "(e.g., deliberate removal of error handling or concurrency checks), unless the change introduces a clear and unavoidable bug in the diff itself. "
                "Avoid speculative concerns about external dependencies or unobservable runtime behaviors unless clearly indicated by the diff or supported by the PR description."
        )
    else:
        return (
            "Review the provided code diff and identify critical bugs directly visible in the modified lines, such as syntax errors, null-pointer exceptions, or logical errors "
            "that are explicitly caused by the changes and lead to unavoidable errors in the modified code. "
            "Use the PR description to understand the intent and implications of the changes, and do not flag issues if the PR description explains the reasoning behind a change "
            "(e.g., deliberate removal of error handling or concurrency checks), unless the change introduces a clear and unavoidable bug in the diff itself. "
            "Do not make assumptions about code outside the diff, such as variable definitions, external logic, or potential runtime behaviors. "
            "Do not provide general suggestions, style recommendations, documentation advice, or speculative concerns about issues not directly observable in the diff "
            "(e.g., hypothetical runtime failures contradicted by the PR description)."
        )
