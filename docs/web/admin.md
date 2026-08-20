# DealHunter Administration Web Interface

## Overview

The administration interface provides system monitoring, diagnostics, and configuration management for DealHunter. All admin pages are under the `/admin` URL prefix.

## Routes

| Route | Method | Description |
|---|---|---|
| `/admin` | GET | System overview dashboard |
| `/admin/account` | GET | Account diagnostics (read-only) |
| `/admin/account/check` | POST | Check account connectivity (network) |
| `/admin/runs` | GET | Paginated run history |
| `/admin/runs/<run_id>` | GET | Run detail |
| `/admin/events` | GET | Structured error events |
| `/admin/doctor` | GET | System diagnostics (local only) |
| `/admin/doctor/check` | POST | Diagnostics with network |
| `/admin/database` | GET | Database stats and schema |
| `/admin/database/backup` | POST | Create database backup |
| `/admin/database/integrity` | POST | Run integrity check |
| `/admin/settings` | GET | Configuration with precedence |
| `/admin/settings/update` | POST | Update safe-editable setting |

## UX Principles

The admin interface follows:

```
STATUS → EXPLANATION → SAFE ACTION → TECHNICAL DETAIL
```

## Network Safety

- **Page loads produce 0 external requests**
- Network actions require explicit user interaction (button click)
- Network-requiring actions: Account check, Doctor with network
- All network actions are POST with CSRF protection

## Account Diagnostics

- Read-only
- Token is ephemeral (environment variable only)
- Never displays or persists: tokens, cookies, email, phone, names, addresses, payments
- Opening the page does NOT trigger network requests
- "Check connectivity" is an explicit opt-in action

## Runs

- Paginated listing (20 per page)
- Filter by status: COMPLETED, PARTIAL, PARTIAL_RUN, FAILED, RUNNING
- Run detail shows: duration, observation count, product count, store count, timestamps
- HTMX pagination for smooth navigation
- Does not expose location coordinates

## Events / Errors

- Structured events from failed/partial runs
- Severity classification (ERROR / WARNING)
- Error codes from existing structured errors
- Component tracking
- Links to run detail
- NOT a raw log viewer

## Doctor

- Default: LOCAL ONLY checks (Configuration, Database, SQLite integrity, Schema, Permissions, Disk space, Last run, Partial runs)
- Shows overall health status on page load
- Network diagnostics via explicit "Run diagnostic with network" button (POST + CSRF)
- Displays: Catalog, Turbo, Restaurants, Account, Database, SQLite integrity, Schema, Overall

## Database

- Shows: path, size, schema version, products, observations, stores, runs, alerts, watchlist, last run, last observation
- Schema table with row counts
- Safe actions only: Integrity check, Create backup
- NO: arbitrary SQL, DROP, DELETE, reset, restore, VACUUM via web

## Settings

Configuration display with:

- **Effective value**: the actual value being used
- **Origin**: where the value comes from (config.toml or default)
- **Classification**:
  - `SAFE_EDITABLE`: can be modified via web interface
  - `READ_ONLY`: visible but not web-editable
  - `SECRET_FORBIDDEN`: masked, never displayed or editable

Precedence:

```
CLI > Profile > config.toml > Default
```

Settings are saved using the existing config layer (`save_config`), not manual TOML string replacement.

Theme, density, cards/table are localStorage preferences, not global config.

## CSRF Protection

- All POST endpoints require CSRF token
- Token is generated per session and injected via `csrf_token` context processor
- Can be sent via form field `csrf_token` or header `X-CSRF-Token`
- Invalid/missing CSRF returns HTTP 400

## Security

- Server binds to `127.0.0.1` by default
- No sensitive data in templates (tokens, passwords, emails, etc.)
- Run IDs displayed truncated in lists
- Location coordinates not exposed in run detail
- No arbitrary SQL execution
- Input validation on settings updates
- CSRF on all state-changing operations
- Path traversal prevention via Flask's blueprint routing
- XSS prevention via Jinja2 auto-escaping + `markupsafe.escape`

## Responsive Design

- Uses Bootstrap 5 responsive grid
- Desktop: full sidebar navigation with admin sub-links
- Mobile: collapsible navigation, responsive tables
- Cards and tables adapt to screen size
- Status badges and icons for quick scanning
