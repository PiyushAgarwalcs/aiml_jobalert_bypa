"""
Migration script from V1 JSON history to V2 SQLite database.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from database.db_manager import DBManager
from core.models import JobListing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_json_to_sqlite(json_path: str, sqlite_path: str):
    if not os.path.exists(json_path):
        logger.warning(f"No JSON history file found at {json_path}. Nothing to migrate.")
        return

    logger.info(f"Initializing V2 Database at {sqlite_path}")
    db_manager = DBManager(sqlite_path)
    await db_manager.init_db()

    logger.info(f"Loading {json_path}...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read JSON: {e}")
        return

    jobs_data = data.get("jobs", {})
    if not jobs_data:
        logger.info("No jobs found in JSON to migrate.")
        return

    logger.info(f"Found {len(jobs_data)} jobs in JSON. Converting to JobListing...")
    jobs_to_insert = []
    
    for job_id, entry in jobs_data.items():
        try:
            job = JobListing(
                company_name=entry.get("company", "Unknown"),
                job_title=entry.get("role", "Unknown"),
                location=entry.get("location", "Unknown"),
                apply_url=entry.get("apply_url", "Unknown"),
                source_platform=entry.get("source", "Unknown"),
                salary=entry.get("salary"),
                estimated_salary_lpa=entry.get("estimated_salary_lpa"),
                company_prestige_score=entry.get("prestige_score", 5),
            )
            # Override generated ID/timestamps with historical ones if available
            job.job_id = job_id 
            job.discovery_timestamp = entry.get("first_seen", datetime.now(timezone.utc).isoformat())
            job.last_seen = entry.get("last_seen", job.discovery_timestamp)
            
            jobs_to_insert.append(job)
        except Exception as e:
            logger.error(f"Error converting job {job_id}: {e}")

    logger.info(f"Inserting {len(jobs_to_insert)} jobs into SQLite...")
    await db_manager.save_jobs(jobs_to_insert)
    logger.info("Migration complete!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate Jobs JSON to SQLite")
    parser.add_argument("--json", type=str, default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "jobs_history.json"))
    parser.add_argument("--db", type=str, default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "jobs.db"))
    
    args = parser.parse_args()
    asyncio.run(migrate_json_to_sqlite(args.json, args.db))
