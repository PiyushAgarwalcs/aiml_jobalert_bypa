"""
AI/ML Fresher Job Discovery System V2
Fully asynchronous, configuration-driven, SQLite-backed pipeline.
"""

import asyncio
import argparse
import logging
import logging.config
import os
import sys
import time
from datetime import datetime, timezone

from config.settings import (
    DB_PATH, TOP_N_JOBS, DRY_RUN, IST, LOGGING_CONFIG, LOGS_DIR, NOTIFY_ON_EMPTY
)
from database.db_manager import DBManager
from scrapers.scraper_manager import ScraperManager
from core.filter_engine import FilterEngine
from core.dedup_engine import DedupEngine
from core.ranking_engine import RankingEngine
from notifications.telegram_bot import TelegramBot
from reports.report_generator import ReportGenerator

def setup_logging():
    # Setup standard python logging from the JSON config
    log_file = os.path.join(LOGS_DIR, "job_alert.log")
    
    # We will just setup basic config here programmatically for reliability
    # using parameters from LOGGING_CONFIG
    log_format = LOGGING_CONFIG.get("format", "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s")
    date_format = LOGGING_CONFIG.get("date_format", "%Y-%m-%d %H:%M:%S")
    level = getattr(logging, LOGGING_CONFIG.get("level", "INFO"))
    
    import io
    utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    
    handlers = [logging.StreamHandler(utf8_stdout)]
    
    # Add File Handler
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=LOGGING_CONFIG.get("max_bytes", 10485760),
            backupCount=LOGGING_CONFIG.get("backup_count", 5),
            encoding="utf-8"
        )
        handlers.append(file_handler)
    except Exception as e:
        print(f"Failed to setup file handler: {e}")
        
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

async def async_main():
    parser = argparse.ArgumentParser(description="V2 Job Discovery System")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-notify", action="store_true")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("main")
    
    is_dry_run = DRY_RUN or args.dry_run

    now_ist = datetime.now(IST)
    workflow_start = datetime.now(timezone.utc).isoformat()
    start_time = time.time()
    
    logger.info("═" * 60)
    logger.info("🚀 AI/ML Fresher Job Discovery System V2 (Async)")
    logger.info(f"   Time: {now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")
    logger.info(f"   Dry Run: {is_dry_run}")
    logger.info("═" * 60)

    try:
        # 1. Init Database
        logger.info("\n📂 Step 1: Initializing Database...")
        db_manager = DBManager(DB_PATH)
        await db_manager.init_db()
        known_job_ids = await db_manager.get_all_job_ids()
        logger.info(f"   Known historical jobs: {len(known_job_ids)}")

        # Prune jobs older than 90 days to keep dedup set lean
        pruned = await db_manager.prune_old_jobs(days=90)
        if pruned:
            known_job_ids = await db_manager.get_all_job_ids()  # refresh after prune

        # 2. Scrape All Sources Asynchronously
        logger.info("\n🔍 Step 2: Async Scraping...")
        scraper_manager = ScraperManager(db_manager)
        raw_jobs, scrape_stats = await scraper_manager.scrape_all()
        logger.info(f"   Raw jobs collected: {len(raw_jobs)}")
        
        if not raw_jobs:
            logger.warning("⚠ No jobs collected from any source!")
            await db_manager.record_workflow_run({
                "started_at": workflow_start,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "runtime": time.time() - start_time,
                "companies_checked": scrape_stats["total_sources"],
                "companies_failed": scrape_stats["failed_sources"],
            })
            return 0

        # 3. Filter
        logger.info("\n🔧 Step 3: Filtering jobs...")
        filter_engine = FilterEngine()
        filtered_jobs = filter_engine.filter_jobs(raw_jobs)
        
        # 4. Dedup within current run
        logger.info("\n🔄 Step 4: Deduplicating...")
        dedup_engine = DedupEngine()
        unique_jobs = dedup_engine.deduplicate(filtered_jobs)
        
        # 5. Find New Jobs
        logger.info("\n🆕 Step 5: Finding new jobs...")
        new_jobs = dedup_engine.find_new_jobs(unique_jobs, known_job_ids)
        logger.info(f"   New jobs found: {len(new_jobs)}")

        # 6. Rank Jobs
        logger.info("\n📊 Step 6: Ranking jobs...")
        ranking_engine = RankingEngine()
        ranked_all = ranking_engine.rank_jobs(unique_jobs)
        ranked_new = ranking_engine.rank_jobs(new_jobs) if new_jobs else []

        # 7. Select Jobs for Notification
        top_jobs = ranked_new[:TOP_N_JOBS]
        logger.info(f"\n🏆 Step 7: {len(top_jobs)} jobs selected for notification")
        
        # 8. Notifications
        notifications_sent = 0
        if not args.skip_notify and not is_dry_run:
            logger.info("\n📱 Step 8: Sending Telegram notification...")
            bot = TelegramBot()
            if bot.test_connection():
                # Skip empty-run ping unless NOTIFY_ON_EMPTY=true
                if not top_jobs and not NOTIFY_ON_EMPTY:
                    logger.info("   No new jobs and NOTIFY_ON_EMPTY=false — skipping ping")
                elif bot.send_job_alerts(top_jobs, scrape_stats):
                    notifications_sent = len(top_jobs)
        else:
            logger.info("\n📱 Step 8: Skipping Telegram (--skip-notify or DRY_RUN)")

        # 9. Reports
        logger.info("\n📄 Step 9: Generating reports...")
        report_gen = ReportGenerator(db_manager)
        await report_gen.generate_all()

        # 10. Save to DB
        logger.info("\n💾 Step 10: Saving to SQLite...")
        await db_manager.save_jobs(unique_jobs)
        for job in top_jobs:
            if not is_dry_run and not args.skip_notify:
                await db_manager.mark_notification_sent(job.job_id)

        # Record workflow stats
        runtime = time.time() - start_time
        await db_manager.record_workflow_run({
            "started_at": workflow_start,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "runtime": runtime,
            "jobs_found": len(raw_jobs),
            "duplicates": len(raw_jobs) - len(unique_jobs),
            "notifications_sent": notifications_sent,
            "companies_checked": scrape_stats["total_sources"],
            "companies_failed": scrape_stats["failed_sources"]
        })

        logger.info("\n" + "═" * 60)
        logger.info("✅ Pipeline Complete!")
        logger.info(f"   ⏱  Time: {runtime:.1f}s")
        logger.info(f"   📥 Raw jobs: {len(raw_jobs)}")
        logger.info(f"   🆕 New jobs: {len(new_jobs)}")
        logger.info(f"   🏆 Sent: {notifications_sent}")
        logger.info("═" * 60)

        return 0

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        return 1

def main():
    return asyncio.run(async_main())

if __name__ == "__main__":
    sys.exit(main())
