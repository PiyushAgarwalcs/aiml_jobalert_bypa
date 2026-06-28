"""
History manager for the AI/ML Job Alert System.
Manages jobs_history.json to track seen jobs across runs and prevent duplicates.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from core.models import JobListing

logger = logging.getLogger(__name__)


class HistoryManager:
    """Manages persistent job history for dedup across runs."""

    def __init__(self, history_file: str):
        self.history_file = history_file
        self.history: dict[str, Any] = {"last_run_timestamp": None, "jobs": {}}

    def load(self) -> set[str]:
        """
        Load history from JSON file.
        Returns set of all known job_ids.
        """
        if not os.path.exists(self.history_file):
            logger.warning(f"History file not found: {self.history_file}. Starting fresh.")
            return set()

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                self.history = json.load(f)

            job_ids = set(self.history.get("jobs", {}).keys())
            last_run = self.history.get("last_run_timestamp")
            logger.info(
                f"Loaded history: {len(job_ids)} known jobs. "
                f"Last run: {last_run or 'Never'}"
            )
            return job_ids

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading history file: {e}. Starting fresh.")
            self.history = {"last_run_timestamp": None, "jobs": {}}
            return set()

    def update(self, jobs: list[JobListing]) -> None:
        """
        Add or update jobs in history.
        - New jobs get first_seen = now
        - Existing jobs get last_seen = now
        """
        now = datetime.now(timezone.utc).isoformat()

        for job in jobs:
            if job.job_id in self.history["jobs"]:
                # Update last_seen for existing job
                self.history["jobs"][job.job_id]["last_seen"] = now
            else:
                # Add new job
                entry = job.to_history_entry()
                entry["first_seen"] = now
                entry["last_seen"] = now
                self.history["jobs"][job.job_id] = entry

        self.history["last_run_timestamp"] = now
        logger.info(f"History updated: {len(self.history['jobs'])} total jobs tracked")

    def save(self) -> None:
        """Save history to JSON file."""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            logger.info(f"History saved to {self.history_file}")
        except OSError as e:
            logger.error(f"Failed to save history: {e}")

    def get_last_run_timestamp(self) -> str | None:
        """Return the timestamp of the last execution."""
        return self.history.get("last_run_timestamp")

    def get_stats(self) -> dict:
        """Return summary statistics about the history."""
        jobs = self.history.get("jobs", {})
        companies = set()
        for entry in jobs.values():
            companies.add(entry.get("company", "Unknown"))

        return {
            "total_jobs_tracked": len(jobs),
            "unique_companies": len(companies),
            "last_run": self.history.get("last_run_timestamp"),
        }

    def cleanup_old_entries(self, max_age_days: int = 90) -> int:
        """Remove entries older than max_age_days to prevent file bloat."""
        now = datetime.now(timezone.utc)
        to_remove = []

        for job_id, entry in self.history.get("jobs", {}).items():
            try:
                last_seen_str = entry.get("last_seen", "")
                last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
                age_days = (now - last_seen).days
                if age_days > max_age_days:
                    to_remove.append(job_id)
            except (ValueError, TypeError):
                continue

        for job_id in to_remove:
            del self.history["jobs"][job_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} entries older than {max_age_days} days")

        return len(to_remove)
