# DealHunter Scheduler Operations

The automated execution of DealHunter is managed natively through `cron` (or `crond` in Termux). This allows the crawler and Alerts Engine (Deal Watcher) to run autonomously in the background.

## Standard Cadence
The recommended live rollout cadence executes 4 times a day to capture intraday price adjustments and flash deals without risking rate limits or account blocks:
- **07:00** (Morning updates)
- **10:00** (Mid-morning sweeps)
- **13:00** (Lunchtime promotions)
- **19:00** (Evening deals)

Timezone defaults to your device's local Termux environment timezone.

## How to Enable / Disable
To enable or modify the scheduler, edit the crontab:
```bash
crontab -e
```

**Enable (Example Entry):**
```bash
0 7,10,13,19 * * * cd /data/data/com.termux/files/home/rappi-deal-hunter && DEALHUNTER_SOURCE=SCHEDULED /data/data/com.termux/files/usr/bin/flock -n /tmp/dealhunter.lock bash -c "./bin/rappi-ofertas discover --vertical general && ./bin/dealwatcher" >> logs/crawler-cron.log 2>&1
```

**Disable:**
Run `crontab -e` and comment out (`#`) the DealHunter line, or delete it entirely.

## Check Status & Logs
- **Pending Jobs**: `crontab -l`
- **Crawler & Alert Logs**: `tail -f ~/rappi-deal-hunter/logs/crawler-cron.log`
- **Database Tracking**: `sqlite3 rappi-deals.db "SELECT run_id, started_at, status FROM runs ORDER BY started_at DESC LIMIT 5;"`

## Singleton Lock (Concurrency Protection)
We use `flock -n /tmp/dealhunter.lock` to guarantee that only one crawler can run at a time. If a crawl takes longer than the interval or is triggered manually while the cron is running, the secondary execution is safely rejected to avoid database locking issues or duplicate observations.

## Termux Requirements
- The `cron` daemon must be running. If using Termux:Boot, ensure `crond` is started automatically.
- **Battery Optimization**: Termux must be exempted from Android battery optimizations (`termux-wake-lock`) for background networking to complete successfully.
- **Notification Permissions**: Termux API (`termux-notification`) requires the Termux:API app and Android notification permissions.

## Delivery Failures
Failures in the Termux notification delivery (e.g. API crash) will mark the event's `delivery_status` as `failed` inside `alert_events`, but will *not* crash the crawler or corrupt historical observations. DealHunter does not implement aggressive infinite retries to avoid delayed spam floods.
