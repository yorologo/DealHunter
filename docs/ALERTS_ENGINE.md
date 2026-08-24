# Alerts Engine (Deal Watcher)

The Alerts Engine monitors state transitions across crawler runs to detect meaningful events without spamming the user.

## Core Principles
1. **Incremental Evaluation**: Evaluates only the stores affected by the current crawl.
2. **Snapshot Completeness**: An item is considered `OUT_OF_STOCK` only if the store was fully scraped in the current run and the item is missing.
3. **Partial Run Safety**: If a crawl aborts or hits a timeout, uncrawled stores retain their last known state and do not generate false disappearances.
4. **Channel Separation**: Public promotions and Pro promotions are tracked independently.
5. **Idempotency**: Replaying the same run multiple times will not duplicate events.

## Persistence
Events are stored in `alert_events` (schema v14) with a deterministic `event_key` preventing duplicates for the same run.
Delivery status (`pending`, `sent`, `failed`) is maintained safely without affecting crawler execution.
