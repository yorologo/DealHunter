# Phase 5D.3B — Uber Termux Headless Phone-Only Background Transport

## Decision
**TERMUX_CHROMIUM_PHONE_ONLY_WITH_LOGIN_SETUP**

We validated that the `chromium` package from `x11-repo` can run entirely in background on Termux natively (`--headless`), establishing a robust CDP interface and communicating with Uber Eats without Windows, without Android UI scraping, and without `termux-wake-lock` failures. 

To overcome Uber's location constraints on new profiles, `carbonyl` (a terminal-based Chromium build) was used successfully to perform a one-time "Session Setup" exclusively through the Termux CLI.

## Chromium Details
- **Package**: `chromium` (from `x11-repo`)
- **Version**: `149.0.7827.155`
- **Sandbox**: Normal (No `--no-sandbox` required!)
- **Headless**: Yes (`--headless`)
- **X11 Required (Normal Run)**: No (Only required X11 dependencies installed, but no X Server needed for execution).

## CDP
- **Local Only**: Yes (127.0.0.1:9223)
- **Target Create**: Integrated successfully into `UberBrowserTransport`.

## Uber Transport
- **Public Without Login**: Returns HTTP 200 and sections, but `items: 0` if default location is out of bounds.
- **Login Required**: Location context required.
- **Session Setup**: Conducted successfully using `carbonyl` (TUI-based browser) to accept cookies and input delivery address.
- **Session Persistence**: PASS. Headless Chromium successfully inherits the Carbonyl session cookies/location.
- **Challenges**: None triggered during the Headless/Carbonyl flow.

## Resources
- **RAM**: Minimal (~80-150MB per process).
- **Storage**: ~171MB for Chromium + dependencies.
- **Seconds Per Store**: ~2-4s (Restaurants) to ~10-15s (Large Groceries).

## Tests
- **Suite**: 418 passed in 51.24s (0 failures).
- **V15 Isolation**: PASS (Rappi crawler unaffected).

