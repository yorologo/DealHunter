import datetime
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FLOCK = shutil.which("flock") or "flock"
SHELL = shutil.which("bash") or "bash"
LOCK_FILE = Path(tempfile.gettempdir()).resolve() / "dealhunter.lock"
LOG_FILE = REPO_ROOT / "logs" / "crawler-cron.log"
CRON_COMMENT = "# DealHunter Scheduler (managed)"
LEGACY_COMMENT = "# DealHunter Daily Sweep"
RUN_HOURS = (7, 10, 13, 19)
RUN_TIMES = tuple((hour, minute) for hour in RUN_HOURS for minute in (0, 30))


def _provider_command(provider):
    runner = shlex.quote(str(REPO_ROOT / "bin" / "rappi-ofertas"))
    watcher = shlex.quote(str(REPO_ROOT / "bin" / "dealwatcher"))
    inner = f"{runner} sync --provider {shlex.quote(provider)} && {watcher}"
    return (
        f"cd {shlex.quote(str(REPO_ROOT))} && DEALHUNTER_SOURCE=SCHEDULED "
        f"{shlex.quote(FLOCK)} -n {shlex.quote(str(LOCK_FILE))} "
        f"{shlex.quote(SHELL)} -c {shlex.quote(inner)} "
        f">> {shlex.quote(str(LOG_FILE))} 2>&1"
    )


RAPPI_JOB = f"0 7,10,13,19 * * * {_provider_command('rappi')}"
UBER_JOB = f"30 7,10,13,19 * * * {_provider_command('uber_eats')}"
MANAGED_LINES = (
    CRON_COMMENT,
    "# DealHunter Rappi Sync",
    RAPPI_JOB,
    "# DealHunter Uber Eats Sync",
    UBER_JOB,
)


def get_crontab():
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    except FileNotFoundError:
        return ""
    if result.returncode == 0:
        return result.stdout
    if result.returncode == 1 and "no crontab" in (result.stderr or "").lower():
        return ""
    raise RuntimeError(f"Could not read crontab: {(result.stderr or '').strip()}")


def set_crontab(content):
    result = subprocess.run(
        ["crontab", "-"], input=content, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Could not install crontab: {(result.stderr or '').strip()}")
    if get_crontab() != content:
        raise RuntimeError("Crontab verification failed: exact readback mismatch")


def _is_managed_line(line):
    stripped = line.strip()
    if stripped in {CRON_COMMENT, LEGACY_COMMENT, "# DealHunter Rappi Sync", "# DealHunter Uber Eats Sync"}:
        return True
    return (
        "DEALHUNTER_SOURCE=SCHEDULED" in stripped
        and ("rappi-ofertas" in stripped or "dealwatcher" in stripped)
    )


def _desired_crontab(existing):
    preserved = [line for line in existing.splitlines() if line.strip() and not _is_managed_line(line)]
    lines = preserved + list(MANAGED_LINES)
    return "\n".join(lines) + "\n"


def is_scheduler_enabled():
    lines = set(get_crontab().splitlines())
    return RAPPI_JOB in lines and UBER_JOB in lines


def _validated_location(config=None):
    if config is None:
        from dealhunter.config import get_merged_config
        config = get_merged_config(None)
    lat = config.get("lat")
    lng = config.get("lng")
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Scheduler requires configured lat/lng before it can be enabled") from exc
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise RuntimeError("Scheduler lat/lng are outside valid coordinate ranges")
    return lat, lng


def enable_scheduler(config=None):
    _validated_location(config)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    cron = get_crontab()
    desired = _desired_crontab(cron)
    if cron == desired:
        return
    set_crontab(desired)


def disable_scheduler():
    cron = get_crontab()
    lines = [line for line in cron.splitlines() if line.strip() and not _is_managed_line(line)]
    desired = ("\n".join(lines) + "\n") if lines else ""
    if cron == desired:
        return
    set_crontab(desired)


def get_next_run():
    if not is_scheduler_enabled():
        return None
    now = datetime.datetime.now()
    for hour, minute in RUN_TIMES:
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > now:
            return candidate
    first_hour, first_minute = RUN_TIMES[0]
    return (now + datetime.timedelta(days=1)).replace(
        hour=first_hour,
        minute=first_minute,
        second=0,
        microsecond=0,
    )
