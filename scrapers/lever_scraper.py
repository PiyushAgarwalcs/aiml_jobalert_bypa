"""
Lever ATS API scraper for the AI/ML Job Alert System.
Uses the free, public Lever Postings API to fetch jobs from companies
that use Lever as their applicant tracking system.

API: https://api.lever.co/v0/postings/{company}?mode=json
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from config.search_terms import ATS_TITLE_KEYWORDS
from core.models import JobListing
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

LEVER_API_BASE = "https://api.lever.co/v0/postings"


class LeverScraper(BaseScraper):
    """Scrapes jobs from companies using Lever ATS via their public API."""

    def __init__(self):
        super().__init__("lever", session, semaphore)
        self.companies = get_lever_companies()

    def scrape(self) -> list[JobListing]:
        """Scrape all Lever companies for AI/ML jobs."""
        all_jobs = []

        for company in self.companies:
            try:
                jobs = self._scrape_company(company)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.warning(f"[lever] Failed to scrape {company.name}: {e}")
                continue

        return all_jobs

    def _scrape_company(self, company: CompanyInfo) -> list[JobListing]:
        """Scrape a single company's Lever postings."""
        url = f"{LEVER_API_BASE}/{company.ats_board_token}"
        params = {"mode": "json"}

        data = self._get_json(url, params=params)
        if data is None or not isinstance(data, list):
            return []

        jobs = []
        for posting in data:
            job = self._parse_posting(posting, company)
            if job and self._is_relevant(job):
                jobs.append(job)

        logger.debug(f"[lever] {company.name}: {len(jobs)} relevant AI/ML jobs from {len(data)} total")
        return jobs

    def _parse_posting(self, data: dict, company: CompanyInfo) -> Optional[JobListing]:
        """Parse a single Lever posting."""
        try:
            text = data.get("text", "").strip()
            if not text:
                return None

            # Location
            categories = data.get("categories", {})
            location = categories.get("location", "Not specified")
            if isinstance(location, list):
                location = ", ".join(location) if location else "Not specified"

            # Department / Team
            team = categories.get("team", "")
            department = categories.get("department", "")
            commitment = categories.get("commitment", "")  # e.g., "Full-time"

            # Posting date
            created_at = data.get("createdAt")
            posting_date = None
            if created_at:
                try:
                    # Lever uses millisecond timestamps
                    posting_date = datetime.fromtimestamp(
                        created_at / 1000, tz=timezone.utc
                    ).isoformat()
                except (ValueError, TypeError, OSError):
                    pass

            # Apply URL
            apply_url = data.get("hostedUrl") or data.get("applyUrl", "")

            # Description
            description_plain = data.get("descriptionPlain", "")
            description_summary = description_plain[:500] if description_plain else ""

            # Additional lists (requirements, responsibilities)
            lists_data = data.get("lists", [])
            for lst in lists_data:
                list_text = lst.get("text", "")
                list_content = lst.get("content", "")
                if "qualif" in list_text.lower() or "require" in list_text.lower():
                    # Append requirements to description
                    import re
                    clean_content = re.sub(r"<[^>]+>", " ", list_content)
                    description_summary += " " + clean_content[:300]

            context = f"{team} {department}".strip()

            return JobListing(
                company_name=company.name,
                job_title=text,
                location=location,
                apply_url=apply_url,
                source_platform="lever",
                posting_date=posting_date,
                job_description_summary=(description_summary + " " + context).strip(),
                experience_required=commitment,
                company_category=company.category,
                company_prestige_score=company.prestige_score,
                estimated_salary_lpa=company.estimated_salary_lpa,
                salary_confidence="medium" if company.estimated_salary_lpa else None,
            )

        except Exception as e:
            logger.debug(f"[lever] Error parsing posting from {company.name}: {e}")
            return None

    def _is_relevant(self, job: JobListing) -> bool:
        """Check if a job title matches AI/ML keywords."""
        title_lower = f" {job.job_title.lower()} "
        desc_lower = (job.job_description_summary or "").lower()
        combined = title_lower + " " + desc_lower

        for keyword in ATS_TITLE_KEYWORDS:
            if keyword in combined:
                return True

        return False
