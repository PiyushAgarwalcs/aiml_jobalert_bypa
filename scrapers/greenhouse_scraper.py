"""
Greenhouse ATS API scraper for the AI/ML Job Alert System.
Uses the free, public Greenhouse Boards API to fetch jobs from companies
that use Greenhouse as their applicant tracking system.

API Docs: https://developers.greenhouse.io/job-board.html
Endpoint: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from config.search_terms import ATS_TITLE_KEYWORDS, ALL_ACCEPTED_LOCATIONS
from core.models import JobListing
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseScraper(BaseScraper):
    """Scrapes jobs from companies using Greenhouse ATS via their public API."""

    def __init__(self):
        super().__init__("greenhouse", session, semaphore)
        self.companies = get_greenhouse_companies()

    def scrape(self) -> list[JobListing]:
        """Scrape all Greenhouse companies for AI/ML jobs."""
        all_jobs = []

        for company in self.companies:
            try:
                jobs = self._scrape_company(company)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.warning(f"[greenhouse] Failed to scrape {company.name}: {e}")
                continue

        return all_jobs

    def _scrape_company(self, company: CompanyInfo) -> list[JobListing]:
        """Scrape a single company's Greenhouse board."""
        url = f"{GREENHOUSE_API_BASE}/{company.ats_board_token}/jobs"
        params = {"content": "true"}  # Include job description

        data = self._get_json(url, params=params)
        if data is None:
            return []

        jobs_data = data.get("jobs", [])
        if not jobs_data:
            logger.debug(f"[greenhouse] No jobs found for {company.name}")
            return []

        jobs = []
        for job_data in jobs_data:
            job = self._parse_job(job_data, company)
            if job and self._is_relevant(job):
                jobs.append(job)

        logger.debug(f"[greenhouse] {company.name}: {len(jobs)} relevant AI/ML jobs from {len(jobs_data)} total")
        return jobs

    def _parse_job(self, data: dict, company: CompanyInfo) -> Optional[JobListing]:
        """Parse a single job from Greenhouse API response."""
        try:
            title = data.get("title", "").strip()
            if not title:
                return None

            # Extract location
            location = self._extract_location(data)

            # Extract posting date
            updated_at = data.get("updated_at", "")
            posting_date = None
            if updated_at:
                try:
                    posting_date = datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    ).isoformat()
                except ValueError:
                    pass

            # Build apply URL
            absolute_url = data.get("absolute_url", "")
            apply_url = absolute_url or f"https://boards.greenhouse.io/{company.ats_board_token}/jobs/{data.get('id', '')}"

            # Extract description summary (first 500 chars, stripped of HTML)
            content = data.get("content", "")
            description_summary = self._clean_html(content)[:500] if content else ""

            # Extract department/team
            departments = data.get("departments", [])
            dept_names = [d.get("name", "") for d in departments]
            dept_str = ", ".join(dept_names)

            return JobListing(
                company_name=company.name,
                job_title=title,
                location=location,
                apply_url=apply_url,
                source_platform="greenhouse",
                posting_date=posting_date,
                job_description_summary=description_summary + " " + dept_str,
                company_category=company.category,
                company_prestige_score=company.prestige_score,
                estimated_salary_lpa=company.estimated_salary_lpa,
                salary_confidence="medium" if company.estimated_salary_lpa else None,
            )

        except Exception as e:
            logger.debug(f"[greenhouse] Error parsing job from {company.name}: {e}")
            return None

    def _extract_location(self, data: dict) -> str:
        """Extract location from Greenhouse job data."""
        location_data = data.get("location", {})
        if isinstance(location_data, dict):
            return location_data.get("name", "Not specified")
        elif isinstance(location_data, str):
            return location_data
        return "Not specified"

    def _is_relevant(self, job: JobListing) -> bool:
        """Check if a job title matches AI/ML keywords."""
        title_lower = f" {job.job_title.lower()} "
        desc_lower = (job.job_description_summary or "").lower()
        combined = title_lower + " " + desc_lower

        for keyword in ATS_TITLE_KEYWORDS:
            if keyword in combined:
                return True

        return False

    def _clean_html(self, html: str) -> str:
        """Strip HTML tags from content."""
        import re
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()
