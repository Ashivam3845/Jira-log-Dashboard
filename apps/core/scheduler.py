"""
Centralized scheduler setup and registration utilities using APScheduler.
"""

from typing import Callable

import pytz
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

from .configs import settings
from .logger import logger

# Registry for functions decorated with @schedule
_schedule_registry = []

# APScheduler configuration
executors = {
    "default": ThreadPoolExecutor(20),
    "processpool": ProcessPoolExecutor(5),
}
job_defaults = {"coalesce": False, "max_instances": 3}

scheduler = BackgroundScheduler(
    executors=executors,
    job_defaults=job_defaults,
    timezone=pytz.timezone(settings.TIME_ZONE),
)


def schedule(trigger: str, **trigger_args):
    """
    Decorator to register a function as a scheduled job.

    Args:
        trigger (str): APScheduler trigger type (e.g., "interval", "cron").
        trigger_args: Arguments for the trigger.

    Returns:
        Callable: The original function with schedule metadata stored.
    """

    def decorator(func: Callable):
        _schedule_registry.append((func, trigger, trigger_args))
        return func

    return decorator


def register_schedules() -> None:
    """
    Register all scheduled jobs stored in the registry and start the scheduler.
    """
    logger.info("Registering schedules...")

    if not _schedule_registry:
        logger.info("No schedules found to register.")
        return

    if scheduler.running:
        logger.info("Scheduler already running, skipping registration.")
        return

    for func, trigger, trigger_args in _schedule_registry:
        scheduler.add_job(
            func,
            trigger,
            **trigger_args,
            replace_existing=True,
        )
        logger.info(
            "Registered job: %s | Trigger: %s | Args: %s",
            func.__name__,
            trigger,
            trigger_args,
        )

    scheduler.start()
    logger.info("Scheduler started successfully.")
