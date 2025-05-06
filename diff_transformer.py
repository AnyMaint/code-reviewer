from unidiff import PatchSet


def transform_diff_to_readable(diff_content: str) -> str:
    """
    Parse a unified diff string and transform it into a readable format for LLM prompts.
    Includes context lines before and after each change.
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
            # Collect context lines for the hunk
            context_lines = [(line.target_line_no or line.source_line_no, line.value.rstrip('\n'))
                             for line in hunk if not (line.is_added or line.is_removed)]
            added_lines = []

            for line in hunk:
                if line.is_removed:
                    file_changes.append({
                        'type': 'Deleted',
                        'old_line': line.source_line_no,
                        'code': line.value.rstrip('\n'),
                        'context': _infer_context(line.value, hunk),
                        'context_before': _get_context_before(line.source_line_no, context_lines, is_source=True),
                        'context_after': _get_context_after(line.source_line_no, context_lines, is_source=True)
                    })
                elif line.is_added:
                    added_lines.append({
                        'type': 'Added',
                        'new_line': line.target_line_no,
                        'code': line.value.rstrip('\n'),
                        'context': _infer_context(line.value, hunk),
                        'context_before': _get_context_before(line.target_line_no, context_lines, is_source=False),
                        'context_after': _get_context_after(line.target_line_no, context_lines, is_source=False)
                    })

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
                    'context': added_lines[0]['context'],
                    'context_before': added_lines[0]['context_before'],
                    'context_after': added_lines[0]['context_after']
                })

        # Detect modifications (deleted + added lines in the same hunk)
        modified_changes = []
        for i, change in enumerate(file_changes):
            if change['type'] == 'Deleted':
                for j, next_change in enumerate(file_changes):
                    if next_change['type'] == 'Added' and next_change['new_line'].startswith(str(change['old_line'])):
                        modified_changes.append({
                            'type': 'Modified',
                            'new_line': next_change['new_line'].split('-')[0],
                            'old_code': change['code'],
                            'new_code': next_change['code'],
                            'context': change['context'],
                            'context_before': change['context_before'],
                            'context_after': change['context_after']
                        })
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
                    indented_code = change['code'].replace('\n', '\n       ')
                    change_text += f"   - Line in new file: {change['new_line']}\n"
                    change_text += f"   - Code:\n       {indented_code}\n"
                elif change['type'] == 'Modified':
                    change_text += f"   - Line in new file: {change['new_line']}\n"
                    change_text += f"   - Old Code: {change['old_code']}\n"
                    change_text += f"   - New Code: {change['new_code']}\n"
                change_text += f"   - Context: {change['context']}\n"
                if change['context_before']:
                    change_text += f"   - Context Before:\n       {change['context_before']}\n"
                if change['context_after']:
                    change_text += f"   - Context After:\n       {change['context_after']}\n"
            changes.append(change_text)

    return "\n".join(changes) or "No changes detected."


def _infer_context(line: str, hunk) -> str:
    """Infer the context of a change (e.g., method or block)."""
    context_lines = [line.value for line in hunk if not (line.is_added or line.is_removed)]
    for ctx_line in context_lines:
        ctx_line = ctx_line.rstrip('\n')
        if 'constructor' in ctx_line:
            return "Inside constructor"
        if 'function' in ctx_line or '(' in ctx_line or ':' in ctx_line or '=>' in ctx_line:
            return "Inside method/function"
        if 'class' in ctx_line or '@' in ctx_line:
            return "At class level"
    if 'constructor' in line:
        return "Inside constructor"
    if '(' in line or ':' in line or '=>' in line:
        return "Inside method/function"
    return "At class level"


def _get_context_before(line_no: int, context_lines: list, is_source: bool) -> str:
    """Get up to 2 context lines before the given line number."""
    key = 0 if is_source else 1  # source_line_no or target_line_no
    before_lines = [line[1] for line in context_lines if line[0] < line_no]
    return '\n'.join(before_lines[-2:]) if before_lines else ""


def _get_context_after(line_no: int, context_lines: list, is_source: bool) -> str:
    """Get up to 2 context lines after the given line number."""
    key = 0 if is_source else 1
    after_lines = [line[1] for line in context_lines if line[0] > line_no]
    return '\n'.join(after_lines[:2]) if after_lines else ""
