from unidiff import PatchSet


def transform_diff_to_readable(diff_content: str) -> str:
    """
    Parse a unified diff string and transform it into a hybrid diff/text format for LLM prompts.
    Each hunk includes a header with file and line numbers, followed by diff-like changes in Markdown code blocks.
    Includes context lines before and after each change.
    Returns a string with change descriptions.
    """
    if not diff_content or not isinstance(diff_content, str):
        raise ValueError("Invalid diff content: must be a non-empty string")

    # Parse diff with unidiff
    try:
        patch = PatchSet(diff_content)
    except Exception as e:
        return f"Error parsing diff: {str(e)}\nPlease check the diff format."

    changes = []

    for file_diff in patch:
        filename = file_diff.target_file.lstrip('b/')  # Remove 'b/' from target path

        for hunk in file_diff:
            # Collect context lines for before/after
            context_lines = [(line.target_line_no or line.source_line_no, line.value.rstrip('\n'))
                             for line in hunk if not (line.is_added or line.is_removed)]

            # Hunk header (outside code block)
            header = f"change in file {filename}, old file line: {hunk.source_start}, new file line: {hunk.target_start}"
            hunk_text = [header, "```"]

            # Get context before the hunk
            context_before = _get_context_before(hunk.source_start if hunk.source_lines else hunk.target_start,
                                                 context_lines, is_source=hunk.source_lines)
            if context_before:
                hunk_text.append(context_before)

            # Add hunk lines in diff format
            for line in hunk:
                prefix = ' '
                if line.is_added:
                    prefix = '+'
                elif line.is_removed:
                    prefix = '-'
                # Process line.value outside f-string to avoid backslash issues
                cleaned_line = line.value.rstrip('\n')
                hunk_text.append(f"{prefix}{cleaned_line}")

            # Get context after the hunk
            last_line_no = (hunk.target_start + hunk.target_length - 1) if hunk.target_lines else \
                (hunk.source_start + hunk.source_length - 1)
            context_after = _get_context_after(last_line_no, context_lines, is_source=not hunk.target_lines)
            if context_after:
                hunk_text.append(context_after)

            # Close code block
            hunk_text.append("```")

            changes.append('\n'.join(hunk_text))

    return '\n\n'.join(changes) or "No changes detected."


def _get_context_before(line_no: int, context_lines: list, is_source: bool) -> str:
    """Get up to 2 context lines before the given line number."""
    key = 0 if is_source else 1
    before_lines = []
    for line in context_lines:
        if line[0] < line_no:
            # Process line content outside f-string
            cleaned_line = line[1]
            before_lines.append(f" {cleaned_line}")
    return '\n'.join(before_lines[-2:]) if before_lines else ""


def _get_context_after(line_no: int, context_lines: list, is_source: bool) -> str:
    """Get up to 2 context lines after the given line number."""
    key = 0 if is_source else 1
    after_lines = []
    for line in context_lines:
        if line[0] > line_no:
            # Process line content outside f-string
            cleaned_line = line[1]
            after_lines.append(f" {cleaned_line}")
    return '\n'.join(after_lines[:2]) if after_lines else ""