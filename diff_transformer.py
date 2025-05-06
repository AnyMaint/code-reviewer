from unidiff import PatchSet


def transform_diff_to_readable(diff_content: str) -> str:
    """
    Parse a unified diff string and transform it into a readable format for LLM prompts.
    Returns a string with explicit change descriptions.
    """
    if not diff_content or not isinstance(diff_content, str):
        raise ValueError("Invalid diff content: must be a non-empty string")

    # Parse diff with unidiff
    patch = PatchSet(diff_content)
    changes = []

    for file_diff in patch:
        filename = file_diff.target_file.lstrip('b/')  # Remove 'b/' from target path
        file_changes = []

        for hunk in file_diff:
            # Track added lines as a block for multi-line additions
            added_lines = []

            for line in hunk:
                if line.is_removed:
                    file_changes.append({
                        'type': 'Deleted',
                        'old_line': line.source_line_no,
                        'code': line.value.rstrip('\n'),
                        'context': _infer_context(line.value, hunk)
                    })
                elif line.is_added:
                    added_lines.append({
                        'type': 'Added',
                        'new_line': line.target_line_no,
                        'code': line.value.rstrip('\n'),
                        'context': _infer_context(line.value, hunk)
                    })
                # Note: unidiff doesn't directly flag 'modified' lines; we detect them by comparing hunks

            # Group consecutive added lines as a single change
            if added_lines:
                start_line = added_lines[0]['new_line']
                end_line = added_lines[-1]['new_line']
                code_block = '\n'.join(change['code'] for change in added_lines)
                line_range = f"{start_line}" if start_line == end_line else f"{start_line}-{end_line}"
                file_changes.append({
                    'type': 'Added',
                    'new_line': line_range,
                    'code': code_block,
                    'context': added_lines[0]['context']
                })

        # Detect modifications (lines that appear in both removed and added in the same hunk)
        modified_changes = []
        for i, change in enumerate(file_changes):
            if change['type'] == 'Deleted':
                # Look for an added line in the same hunk
                for j, next_change in enumerate(file_changes):
                    if next_change['type'] == 'Added' and next_change['new_line'].startswith(str(change['old_line'])):
                        modified_changes.append({
                            'type': 'Modified',
                            'new_line': next_change['new_line'].split('-')[0],  # Use start of range
                            'old_code': change['code'],
                            'new_code': next_change['code'],
                            'context': change['context']
                        })
                        # Mark these changes to be removed
                        change['skip'] = True
                        next_change['skip'] = True
                        break

        # Filter and format changes
        final_changes = [c for c in file_changes if not c.get('skip')] + modified_changes
        if final_changes:
            change_text = f"Changes in {filename}:\n"
            for i, change in enumerate(final_changes, 1):
                change_text += f"{i}. {change['type']}:\n"
                if change['type'] == 'Deleted':
                    change_text += f"   - Line in old file: {change['old_line']}\n"
                    change_text += f"   - Code: {change['code']}\n"
                elif change['type'] == 'Added':
                    # Handle multi-line code blocks with proper indentation
                    indented_code = change['code'].replace('\n', '\n       ')
                    change_text += f"   - Line in new file: {change['new_line']}\n"
                    change_text += f"   - Code:\n       {indented_code}\n"
                elif change['type'] == 'Modified':
                    change_text += f"   - Line in new file: {change['new_line']}\n"
                    change_text += f"   - Old Code: {change['old_code']}\n"
                    change_text += f"   - New Code: {change['new_code']}\n"
                change_text += f"   - Context: {change['context']}\n"
            changes.append(change_text)

    return "\n".join(changes) or "No changes detected."


def _infer_context(line: str, hunk) -> str:
    """Infer the context of a change (e.g., method or block)."""
    # Check hunk context lines for clues
    context_lines = [line.value for line in hunk if not (line.is_added or line.is_removed)]
    for ctx_line in context_lines:
        ctx_line = ctx_line.rstrip('\n')
        if 'constructor' in ctx_line:
            return "Inside constructor"
        if 'function' in ctx_line or '(' in ctx_line or ':' in ctx_line or '=>' in ctx_line:
            return "Inside method/function"
        if 'class' in ctx_line or '@' in ctx_line:
            return "At class level"
    # Fallback based on line content
    if 'constructor' in line:
        return "Inside constructor"
    if '(' in line or ':' in line or '=>' in line:
        return "Inside method/function"
    return "At class level"
