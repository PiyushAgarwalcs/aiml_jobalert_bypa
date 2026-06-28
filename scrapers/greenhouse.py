"""
Greenhouse ATS Scraper — with India/Bangalore location pre-filter.
Only creates JobListings for roles located in India/Bangalore/Remote.
"""
import re
from scrapers.base_scraper import BaseScraper
from core.models import JobListing

_INDIA_RE = re.compile(
    r"bangalore|bengaluru|india|remote|karnataka|hyderabad|pune|chennai|mumbai|delhi|gurugram",
    re.IGNORECASE,
)

class GreenhouseScraper(BaseScraper):
    def __init__(self, session, semaphore):
        super().__init__("Greenhouse", session, semaphore)

    async def scrape(self, company_config) -> list[JobListing]:
        api_url = company_config.get("ats_url")
        if not api_url:
            return []

        data = await self._get_json(api_url)
        if not data or "jobs" not in data:
            return []

        jobs = []
        for job_data in data.get("jobs", []):
            loc = job_data.get("location", {}).get("name", "") or ""
            # Pre-filter: skip if location is set and clearly non-India
            if loc and not _INDIA_RE.search(loc):
                continue

            title = job_data.get("title", "")
            if not title:
                continue

            job = JobListing(
                company_name=company_config["name"],
                job_title=title,
                location=loc or "India",
                apply_url=job_data.get("absolute_url", ""),
                source_platform="greenhouse",
                ats_provider="greenhouse",
                posting_date=job_data.get("updated_at", ""),
                company_category=company_config.get("category"),
                company_prestige_score=company_config.get("prestige_score", 7),
            )
            jobs.append(job)

        return jobs
