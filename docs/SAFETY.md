# Content Safety Pipeline

This document explains how the School of Dandori backend implements the Perspective-based moderation pipeline described in the "Perspective" workshop notebook. The goal is to ensure any request passing through `/api/chat` is screened both before it reaches the LLM and after the LLM responds.

## Overview

1. **Prompt screening** – user inputs are validated with Google Perspective (or a deterministic keyword fallback). Unsafe prompts are blocked before any tool calls or model invocations.
2. **Output screening** – final model completions are re-checked and suppressed if they violate output thresholds.
3. **Auditable logs** – every blocked interaction is recorded with a timestamp, reason, and score snapshot.

## Implementation Details

### Service Layout

```
src/services/
├── chat_service.py      # integrates the safety checks inside stream_chat
└── safety_service.py    # Perspective client, thresholds, fallback logic, logging
assets/safety_thresholds.json  # per-attribute INPUT/OUTPUT limits
```

- `safety_service.check_prompt(text)` returns a `SafetyResult`. If `safe` is `False`, the caller receives the reason string and the request stops.
- `safety_service.check_output(text)` works the same way but enforces tighter thresholds for model responses.
- When blocked, the service calls `log_block(stage=..., text=..., result=...)`. JSON lines are appended to `./logs/safety.log` (override via `SAFETY_LOG_DIR`).

### Perspective Integration

- `PERSPECTIVE_API_KEY` must be set for live calls. We request `TOXICITY`, `IDENTITY_ATTACK`, `SEXUALLY_EXPLICIT`, and `PROFANITY`.
- If the API or key is unavailable, we fall back to keyword heuristics per attribute to avoid silent failures.
- The Perspective client is lazily created and shared via an internal lock to keep startup fast.

### Threshold Configuration

`assets/safety_thresholds.json` ships with defaults inspired by the workshop notebook:

```json
{
  "INPUT": {
    "TOXICITY": 0.65,
    "IDENTITY_ATTACK": 0.45,
    "SEXUALLY_EXPLICIT": 0.50,
    "PROFANITY": 0.55
  },
  "OUTPUT": {
    "TOXICITY": 0.40,
    "IDENTITY_ATTACK": 0.30,
    "SEXUALLY_EXPLICIT": 0.35,
    "PROFANITY": 0.40
  }
}
```

- `INPUT` thresholds are used for prompt checks, `OUTPUT` for response checks.
- Override with `SAFETY_THRESHOLDS_PATH=/path/to/custom_thresholds.json` if different risk tolerances are needed.

### Runtime Flow (`/api/chat`)

1. **Prompt received**
   - `stream_chat` calls `check_prompt`. If blocked, the API responds immediately:
     ```json
     {
       "message": "Prompt blocked by safety system. TOXICITY 1.00 ≥ 0.65 | ...",
       "artifacts": []
     }
     ```
2. **Tool / model execution**
   - Only safe prompts invoke tools/LLMs. Missing OpenAI SDK or API keys trigger the pre-existing deterministic SQL fallback.
3. **Output moderation**
   - Before streaming the final answer, the combined text is passed through `check_output`.
   - Violations substitute the response with a block notice; no unsafe text leaves the server.

### Curl Test Cases

Below are example commands run during integration testing (port `5001` is used to avoid conflicts):

```bash
# Safe prompt (falls back to SQL search because no OpenAI SDK locally)
curl -s -X POST http://127.0.0.1:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about pottery classes"}'

# Unsafe prompt – blocked before model execution
curl -s -X POST http://127.0.0.1:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I support genocide and hate women"}'
```

The second call responds with:

```json
{
  "message": "Prompt blocked by safety system. TOXICITY 1.00 ≥ 0.65 | IDENTITY_ATTACK 1.00 ≥ 0.45",
  "artifacts": []
}
```

This verifies the workshop strategies are fully enforced in the production API.

## Maintenance Tips

- **API keys**: ensure `PERSPECTIVE_API_KEY` is set in `.env` before deploying.
- **Threshold tuning**: start by adjusting `assets/safety_thresholds.json`, then redeploy. Consider separate values for staging vs. production.
- **Log rotation**: `safety.log` uses JSON lines; rotate or ship logs to your observability stack if high volume is expected.
- **Extensibility**: new attributes (e.g., `THREAT`, `INSULT`) can be added by editing `DEFAULT_ATTRIBUTES` and thresholds.

By following this structure, the backend stays aligned with Digital Futures' secure pipeline guidance while keeping the implementation modular and auditable.
