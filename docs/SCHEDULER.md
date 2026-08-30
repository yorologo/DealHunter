# DealHunter Scheduler Operations

The automated execution of DealHunter is managed natively through `cron` (or `crond` in Termux). This allows the multi-provider crawlers and Alerts Engine (Deal Watcher) to run autonomously in the background.

## Standard Cadence
The recommended live rollout cadence executes 4 times a day to capture intraday price adjustments and flash deals. Providers are intentionally staggered by 30 minutes to distribute load and prevent resource contention:

**Rappi:**
- **07:00** (Morning updates)
- **10:00** (Mid-morning sweeps)
- **13:00** (Lunchtime promotions)
- **19:00** (Evening deals)

**Uber Eats:**
- **07:30** (Morning updates)
- **10:30** (Mid-morning sweeps)
- **13:30** (Lunchtime promotions)
- **19:30** (Evening deals)

Timezone defaults to your device's local Termux environment timezone.

## How to Enable / Disable
To enable or modify the scheduler, edit the crontab:
```bash
crontab -e
```

**Enable (Example Entry):**
```bash
# Rappi Sync
0 7,10,13,19 * * * cd /data/data/com.termux/files/home/rappi-deal-hunter && DEALHUNTER_SOURCE=SCHEDULED /data/data/com.termux/files/usr/bin/flock -n /tmp/dealhunter.lock bash -c "PYTHONPATH=src python3 -m dealhunter.cli sync --provider rappi && ./bin/dealwatcher" >> logs/crawler-cron.log 2>&1

# Uber Eats Sync
30 7,10,13,19 * * * cd /data/data/com.termux/files/home/rappi-deal-hunter && DEALHUNTER_SOURCE=SCHEDULED /data/data/com.termux/files/usr/bin/flock -n /tmp/dealhunter.lock bash -c "PYTHONPATH=src python3 -m dealhunter.cli sync --provider uber_eats && ./bin/dealwatcher" >> logs/crawler-cron.log 2>&1
```

**Disable:**
Run `crontab -e` and comment out (`#`) the DealHunter lines.

## Termux Doze / Wake Policy
Android enforces strict power management (Deep Sleep / Doze mode) when the screen is off. We support two operating paradigms:

1. **RELIABLE (Recommended for dedicated devices)**:
   You must acquire a persistent global wake lock (`termux-wake-lock` executed once manually). This guarantees the `crond` scheduler will fire on the exact scheduled minute, but increases battery consumption.
   *Note: Using a script that acquires the wake-lock only when the job starts is insufficient, as the device may be asleep and miss the cron trigger entirely.*

2. **BATTERY_FRIENDLY (Accepts missed/delayed executions)**:
   Do not use a persistent wake-lock. Android will aggressively suspend Termux. Scheduled jobs may fire late (e.g., when you next turn on the screen) or be completely skipped. DealHunter handles this gracefully without data corruption, but you may miss flash deals.

## Check Status & Logs
- **Pending Jobs**: `crontab -l`
- **Crawler & Alert Logs**: `tail -f ~/rappi-deal-hunter/logs/crawler-cron.log`
- **Database Tracking**: `sqlite3 rappi-deals.db "SELECT run_id, started_at, status FROM runs ORDER BY started_at DESC LIMIT 5;"`

## Singleton Lock (Concurrency Protection)
We use `flock -n /tmp/dealhunter.lock` to guarantee that only one crawler can run at a time. If a crawl takes longer than the interval or is triggered manually while the cron is running, the secondary execution is safely rejected to avoid database locking issues or duplicate observations.

## Delivery Failures
Failures in the Termux notification delivery (e.g. API crash) will mark the event's `delivery_status` as `failed` inside `alert_events`, but will *not* crash the crawler or corrupt historical observations. DealHunter does not implement aggressive infinite retries to avoid delayed spam floods.
