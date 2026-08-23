import subprocess
import datetime
import os

CRON_CMD = "cd /data/data/com.termux/files/home/rappi-deal-hunter && DEALHUNTER_SOURCE=SCHEDULED /data/data/com.termux/files/usr/bin/flock -n /tmp/dealhunter.lock ./bin/rappi-ofertas discover --vertical general >> logs/crawler-cron.log 2>&1"
CRON_COMMENT = "# DealHunter Daily Sweep"

def get_crontab():
    try:
        res = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        return res.stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""

def set_crontab(content):
    proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate(input=content.encode('utf-8'))

def is_scheduler_enabled():
    cron = get_crontab()
    return "DEALHUNTER_SOURCE=SCHEDULED" in cron

def enable_scheduler():
    cron = get_crontab()
    if is_scheduler_enabled():
        return
    # Remove old cron entry if exists
    lines = [line for line in cron.split('\n') if line.strip() and "./bin/rappi-ofertas discover" not in line and CRON_COMMENT not in line]
    lines.append(CRON_COMMENT)
    lines.append(f"0 10 * * * {CRON_CMD}")
    set_crontab("\n".join(lines) + "\n")

def disable_scheduler():
    cron = get_crontab()
    if not is_scheduler_enabled():
        return
    lines = [line for line in cron.split('\n') if line.strip() and "DEALHUNTER_SOURCE=SCHEDULED" not in line and CRON_COMMENT not in line]
    set_crontab("\n".join(lines) + "\n")

def get_next_run():
    if not is_scheduler_enabled():
        return None
    now = datetime.datetime.now()
    next_run = now.replace(hour=10, minute=0, second=0, microsecond=0)
    if next_run <= now:
        next_run += datetime.timedelta(days=1)
    return next_run
