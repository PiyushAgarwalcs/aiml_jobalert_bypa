"""
Scraper Manager for AI/ML Job Alert System V2.
Orchestrates async scraping based on configuration and Priority Queue.

Fixes applied:
- Empty results from a scraper no longer count as a failure (Issue #2, #7)
- None detected_ats is handled safely (Issue #4)
- Per-company exception isolation (Issue #10)
- LinkedIn Easy Apply scraper integrated (new feature)
- Startup validation: warns if no companies are configured (Issue #13)
- Disabled source retry period bumped to 72 h in db_manager; here we just
  log it and skip, never crashing the pipeline (Issue #7, #14)
"""
import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Tuple
import time

from core.models import JobListing
from config.settings import MAX_CONCURRENT_REQUESTS, COMPANIES_LIST
from database.db_manager import DBManager
from core.validator import CompanyValidator

from scrapers.greenhouse import GreenhouseScraper
from scrapers.lever import LeverScraper
from scrapers.ashby import AshbyScraper
from scrapers.workday import WorkdayScraper
from scrapers.smartrecruiters import SmartRecruitersScraper
from scrapers.linkedin_scraper import LinkedInEasyApplyScraper

logger = logging.getLogger(__name__)

# ATS name -> scraper class (lazily imported to keep startup fast)
_ATS_MAP = {
    "greenhouse":     ("scrapers.greenhouse",           "GreenhouseScraper"),
    "lever":          ("scrapers.lever",                "LeverScraper"),
    "ashby":          ("scrapers.ashby",                "AshbyScraper"),
    "workday":        ("scrapers.workday",              "WorkdayScraper"),
    "smartrecruiters":("scrapers.smartrecruiters",      "SmartRecruitersScraper"),
    "workable":       ("scrapers.workable",             "WorkableScraper"),
    "jobvite":        ("scrapers.jobvite",              "JobviteScraper"),
    "teamtailor":     ("scrapers.teamtailor",           "TeamTailorScraper"),
    "bamboohr":       ("scrapers.bamboohr",             "BambooHRScraper"),
    "recruitee":      ("scrapers.recruitee",            "RecruiteeScraper"),
    "personio":       ("scrapers.personio",             "PersonioScraper"),
    "comeet":         ("scrapers.comeet",               "ComeetScraper"),
    "icims":          ("scrapers.icims",                "ICIMSScraper"),
    "oracle":         ("scrapers.oracle",               "OracleScraper"),
    "sap":            ("scrapers.sap",                  "SAPScraper"),
    "instahyre":      ("scrapers.instahyre_scraper",    "InstahyreScraper"),
    "github":         ("scrapers.github_scraper",       "GitHubRepoScraper"),
    "custom":         ("scrapers.company_career_scraper", "CustomCareerScraper"),
    "custom_career":  ("scrapers.company_career_scraper", "CustomCareerScraper"),
}


def _build_scraper(ats: str, session, semaphore, db_manager=None):
    """Instantiate the correct scraper for a given ATS name. Returns None if unknown."""
    if ats not in _ATS_MAP:
        return None
    module_path, class_name = _ATS_MAP[ats]
    import importlib
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        # GitHubRepoScraper needs db_manager
        if ats == "github" and db_manager is not None:
            return cls(session, semaphore, db_manager)
        return cls(session, semaphore)
    except Exception as e:
        logger.error(f"Failed to import scraper for ATS '{ats}': {e}", exc_info=True)
        return None


class ScraperManager:
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager

    # ─────────────────────────────────────────────────────────────────────────
    # Per-company processing
    # ─────────────────────────────────────────────────────────────────────────

    async def _process_company(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        company: Dict[str, Any],
    ) -> Tuple[str, bool, float, List[JobListing], str]:
        """
        Process a single company source.
        Returns (name, success, runtime_secs, jobs, error_msg).

        success=True as long as no hard error occurred — returning 0 jobs is
        NOT treated as a failure (companies legitimately post 0 openings).
        """
        start_time = time.time()
        company_name = company.get("name", "Unknown")

        try:
            # 1. Skip disabled sources (with auto-recovery after retry window)
            is_disabled = await self.db_manager.is_source_disabled(company_name)
            if is_disabled:
                logger.info(f"⏭  Skipping {company_name} (temporarily disabled due to consecutive failures)")
                return company_name, False, 0.0, [], "Source disabled"

            # 2. Validate career page + auto-detect ATS
            validator = CompanyValidator(session)
            is_reachable, detected_ats, feed_url, error_msg = await validator.validate_and_detect(company)

            if not is_reachable:
                logger.warning(
                    f"[{company_name}] Career page unreachable: {error_msg}"
                )
                await self.db_manager.update_source_health(
                    company_name, False, time.time() - start_time, 0
                )
                return company_name, False, time.time() - start_time, [], error_msg

            # 3. Resolve ATS — guard against None from validator
            ats = (detected_ats or company.get("ats", "")).strip().lower()
            if not ats:
                ats = company.get("ats", "unknown").strip().lower()

            company["ats"] = ats  # write back for scraper reference

            if feed_url:
                logger.info(f"[{company_name}] RSS feed detected: {feed_url} (using ATS: {ats})")

            # 4. Build scraper
            scraper = _build_scraper(ats, session, semaphore, self.db_manager)
            if scraper is None:
                msg = f"No scraper for ATS '{ats}'"
                logger.warning(f"[{company_name}] {msg}")
                await self.db_manager.update_source_health(
                    company_name, False, time.time() - start_time, 0
                )
                return company_name, False, time.time() - start_time, [], msg

            # 5. Scrape — safe_scrape catches all internal exceptions
            jobs = await scraper.safe_scrape(company)
            runtime = time.time() - start_time

            # FIX #2: returning 0 jobs is SUCCESS (not a failure).
            # Only network/exception paths count as failures.
            await self.db_manager.update_source_health(
                company_name, True, runtime, len(jobs)
            )

            if jobs:
                logger.info(f"[{company_name}] ✓ {len(jobs)} jobs in {runtime:.1f}s")
            else:
                logger.debug(f"[{company_name}] 0 open positions ({runtime:.1f}s) — not a failure")

            return company_name, True, runtime, jobs, ""

        except Exception as e:
            # FIX #10: isolate per-company failures so one crash cannot abort the pipeline
            runtime = time.time() - start_time
            logger.error(
                f"[{company_name}] Unhandled exception during scraping: {e}",
                exc_info=True,
            )
            try:
                await self.db_manager.update_source_health(
                    company_name, False, runtime, 0
                )
            except Exception:
                pass  # DB update failure must never propagate
            return company_name, False, runtime, [], str(e)

    # ─────────────────────────────────────────────────────────────────────────
    # LinkedIn Easy Apply (standalone — not company-config driven)
    # ─────────────────────────────────────────────────────────────────────────

    async def _scrape_linkedin(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
    ) -> List[JobListing]:
        """Run the LinkedIn Easy Apply scraper for Bangalore 12+ LPA jobs."""
        try:
            scraper = LinkedInEasyApplyScraper(session, semaphore)
            jobs = await scraper.safe_scrape({})
            logger.info(f"[LinkedIn Easy Apply] Collected {len(jobs)} jobs")
            return jobs
        except Exception as e:
            logger.error(f"[LinkedIn Easy Apply] Scraper failed: {e}", exc_info=True)
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────────────────────────

    async def scrape_all(self) -> Tuple[List[JobListing], Dict[str, Any]]:
        """Run all scrapers (company configs + LinkedIn Easy Apply)."""

        # FIX #13: Startup validation
        if not COMPANIES_LIST:
            logger.error(
                "❌ STARTUP ERROR: No company configurations found in config/companies/. "
                "Pipeline will only run LinkedIn Easy Apply this cycle."
            )

        logger.info(f"Starting async scrape for {len(COMPANIES_LIST)} configured company sources + LinkedIn Easy Apply.")

        # Deduplicate companies by name; priority companies win conflicts
        unique_companies: Dict[str, Dict] = {}
        for c in COMPANIES_LIST:
            if not c.get("enabled", True):
                continue
            name = c.get("name", "")
            if not name:
                continue
            if name not in unique_companies or c.get("priority", False):
                unique_companies[name] = c

        sorted_companies = sorted(
            unique_companies.values(),
            key=lambda c: (not c.get("priority", False), c.get("name", "")),
        )

        all_jobs: List[JobListing] = []
        stats: Dict[str, Any] = {
            "total_sources": len(sorted_companies) + 1,  # +1 for LinkedIn
            "successful_sources": 0,
            "failed_sources": 0,
            "source_results": {},
        }

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        connector = aiohttp.TCPConnector(ssl=False, limit=MAX_CONCURRENT_REQUESTS)
        timeout = aiohttp.ClientTimeout(total=45, connect=15)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:

            # ── Company-config scrapers ───────────────────────────────────────
            tasks = [
                self._process_company(session, semaphore, company)
                for company in sorted_companies
            ]

            for coro in asyncio.as_completed(tasks):
                try:
                    name, success, runtime, jobs, error_msg = await coro
                except Exception as e:
                    logger.error(f"Unexpected task error: {e}", exc_info=True)
                    stats["failed_sources"] += 1
                    continue

                if success:
                    stats["successful_sources"] += 1
                else:
                    stats["failed_sources"] += 1

                stats["source_results"][name] = {
                    "jobs_found": len(jobs),
                    "time_seconds": round(runtime, 2),
                    "status": "success" if success else "failed",
                    "error": error_msg,
                }
                all_jobs.extend(jobs)

            # ── LinkedIn Easy Apply ───────────────────────────────────────────
            li_jobs = await self._scrape_linkedin(session, semaphore)
            if li_jobs:
                stats["successful_sources"] += 1
            else:
                stats["failed_sources"] += 1

            stats["source_results"]["LinkedIn Easy Apply"] = {
                "jobs_found": len(li_jobs),
                "time_seconds": 0,
                "status": "success" if li_jobs else "no_results",
                "error": "",
            }
            all_jobs.extend(li_jobs)

        logger.info(
            f"Scraping complete — {stats['successful_sources']}/{stats['total_sources']} sources OK, "
            f"{len(all_jobs)} total raw jobs"
        )
        return all_jobs, stats
