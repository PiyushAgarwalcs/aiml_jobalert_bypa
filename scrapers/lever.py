"""
Lever ATS Scraper — with India/Bangalore location pre-filter.
"""
import re
from scrapers.base_scraper import BaseScraper
from core.models import JobListing

_INDIA_RE = re.compile(
    r"bangalore|bengaluru|india|remote|karnataka|hyderabad|pune|chennai|mumbai|delhi|gurugram",
    re.IGNORECASE,
)

class LeverScraper(BaseScraper):
    def __init__(self, session, semaphore):
        super().__init__("Lever", session, semaphore)

    async def scrape(self, company_config) -> list[JobListing]:
        api_url = company_config.get("ats_url")
        if not api_url:
            return []

        data = await self._get_json(api_url)
        if not data or not isinstance(data, list):
            return []

        jobs = []
        for job_data in data:
            cats = job_data.get("categories", {}) or {}
            loc = cats.get("location", "") or ""
            # Pre-filter
            if loc and not _INDIA_RE.search(loc):
                continue

            title = job_data.get("text", "")
            if not title:
                continue

            job = JobListing(
                company_name=company_config["name"],
                job_title=title,
                location=loc or "India",
                apply_url=job_data.get("hostedUrl", ""),
                source_platform="lever",
                ats_provider="lever",
                posting_date=str(job_data.get("createdAt", "")),
                company_category=company_config.get("category"),
                company_prestige_score=company_config.get("prestige_score", 7),
            )
            jobs.append(job)

        return jobs
