# Error Handling

DealHunter uses structured error codes to make failures predictable and actionable.

## Error Codes

| Code | Recoverable | Description | Recommended Action |
|------|-------------|-------------|--------------------|
| `NETWORK_ERROR` | Yes | Network connection failed | Check network connection and retry |
| `TIMEOUT` | Yes | Request timed out | Retry after a moment |
| `HTTP_429` | Yes | Rate limited by server | Wait before retrying. Do not increase request rate |
| `CLOUDFLARE_LIMIT` | No | Blocked by Cloudflare (1015) | Stop requests. Wait at least 5 minutes |
| `INVALID_RESPONSE` | Yes | Unparseable server response | Retry the request |
| `PARSER_ERROR` | No | Failed to parse response data | Report this issue |
| `DB_LOCKED` | Yes | Database locked by another process | Close other processes using the database |
| `DB_CORRUPT` | No | Database file is corrupted | Restore from backup: `rappi-ofertas db backup` |
| `ACCOUNT_SESSION_UNAVAILABLE` | No | Provided token is invalid or expired | Provide a valid token or check account |
| `CONFIG_ERROR` | Yes | Configuration error | Check config: `rappi-ofertas config show` |
| `PARTIAL_RUN` | Yes | Run completed with partial data | Re-run to collect remaining data |
| `REQUEST_BUDGET_REACHED` | No | Max request budget reached | Increase `--max-requests` or accept partial results |

## Partial Runs

When a crawl is interrupted (network error, rate limit, timeout), DealHunter:

1. **Preserves** all observations already committed to the database.
2. **Marks** the run as `PARTIAL` with the specific error code.
3. **Sets** `finished_at` so the run is never left ambiguous.
4. **Saves** a checkpoint with the last completed query and vertical.

Valid data is never rolled back due to an interruption.

## Rate Limiting

DealHunter respects rate limits conservatively:

- On HTTP 429: stops immediately, marks run as PARTIAL.
- On Cloudflare 1015: stops immediately, marks run as PARTIAL.
- Never retries aggressively against rate limits.
- Never implements anti-bot bypasses.

## Doctor

Run diagnostics to check system health:

```bash
rappi-ofertas doctor
```

Output example:

```text
DealHunter Doctor

  Configuration          OK
  Database               OK
  SQLite integrity       OK
  Schema                 OK
  Permissions            OK
  Disk space             OK
  Last run               OK
  Partial runs           0
  Rappi catalog          NOT_CHECKED
  Turbo                  AVAILABLE
  Restaurants            AVAILABLE
  Account context        NOT_CONFIGURED

  Overall              HEALTHY
```

Doctor checks are read-only and do not make network requests by default.
