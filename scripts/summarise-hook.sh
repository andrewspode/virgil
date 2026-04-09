#!/bin/bash
# Fires on UserPromptSubmit. Checks if summaries are needed.
# If so, injects the details into additionalContext for Claude to handle.
cd "$(dirname "${BASH_SOURCE[0]}")/.."
STATUS=$(python3 scripts/session-status.py 2>&1)
if [ $? -ne 0 ]; then
    python3 -c "
import json, sys
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'UserPromptSubmit',
        'additionalContext': sys.argv[1]
    }
}))
" "$STATUS"
fi
