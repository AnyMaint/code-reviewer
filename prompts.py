# prompts.py

GENERAL_PROMPT = "Provide a high-level summary of the pull request based on the title, description, and code changes."
ISSUES_PROMPT = "Review the provided code diff and identify issues, including potential bugs, style improvements, and suggestions for better maintainability."

def get_prompt(mode: str, deep: bool) -> str:
    """
    Returns the appropriate prompt for the given mode, appending a shallow-mode instruction if deep=False.

    Args:
        mode (str): The review mode ('general', 'issues', 'comments').
        deep (bool): Whether to use deep mode (verbose) or shallow mode (bug-focused).

    Returns:
        str: The prepared prompt.

    Raises:
        ValueError: If the mode is unknown.
    """
    if mode == "general":
        base_prompt = GENERAL_PROMPT
    elif mode in ["issues", "comments"]:
        base_prompt = ISSUES_PROMPT
    else:
        raise ValueError(f"Unknown mode: {mode}")

    if not deep:
        shallow_instruction = (
            " Focus exclusively on critical bugs, such as syntax errors, null-pointer exceptions, "
            "or logical errors in the code. Do not provide general suggestions, style recommendations, "
            "documentation advice, or speculative concerns like data migration or external dependencies."
        )
        return base_prompt + shallow_instruction

    return base_prompt
