"""
Google Jobs scraper for the AI/ML Job Alert System.
Uses Google search with structured job search parameters.
"""

import json
import logging
import re
from typing import Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from core.models import JobListing
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_URL = "https://www.google.com/search"


class GoogleJobsScraper(BaseScraper):
    """Scrapes Google search results for job listings."""

    def __init__(self):
        super().__init__("google_jobs", session, semaphore)

    def scrape(self) -> list[JobListing]:
        """Search Google for AI/ML fresher job listings."""
        all_jobs = []

        # Structured search queries targeting job listing pages
        queries = [
            '"machine learning engineer" "fresher" OR "entry level" "bangalore" site:linkedin.com/jobs',
            '"AI engineer" OR "ML engineer" "0-1 years" "india" site:naukri.com',
            '"data scientist" "fresher" OR "new grad" "bangalore" site:linkedin.com/jobs',
            '"machine learning" "fresher" "bangalore" site:cutshort.io',
            '"artificial intelligence" "entry level" "india" site:instahyre.com',
        ]

        for query in queries:
            try:
                self._rotate_user_agent()
                jobs = self._search(query)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.warning(f"[google_jobs] Failed query: {e}")
                continue

        return all_jobs

    def _search(self, query: str) -> list[JobListing]:
        """Execute a Google search and parse results."""
        params = {
            "q": query,
            "num": "15",
            "hl": "en",
        }

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }

        response = self._get(GOOGLE_SEARCH_URL, headers=headers, params=params)
        if response is None:
            return []

        return self._parse_results(response.text)

    def _parse_results(self, html: str) -> list[JobListing]:
        """Parse Google search results for job links."""
        jobs = []

        try:
            soup = BeautifulSoup(html, "lxml")

            # Find all search result links
            results = soup.find_all("div", class_="g")

            for result in results:
                job = self._parse_result(result)
                if job:
                    jobs.append(job)

        except Exception as e:
            logger.warning(f"[google_jobs] Parse error: {e}")

        return jobs

    def _parse_result(self, result) -> Optional[JobListing]:
        """Parse a single Google search result."""
        try:
            # Find the link
            link = result.find("a", href=True)
            if not link:
                return None

            url = link.get("href", "")
            if not url.startswith("http"):
                return None

            # Skip non-job URLs
            job_domains = [
                "linkedin.com/jobs", "naukri.com", "glassdoor.com",
                "indeed.com", "wellfound.com", "foundit.in",
                "greenhouse.io", "lever.co", "careers",
                "cutshort.io", "instahyre.com",
            ]
            if not any(domain in url for domain in job_domains):
                return None

            # Extract title
            title_elem = result.find("h3")
            if not title_elem:
                return None

            raw_title = title_elem.get_text(strip=True)

            # Try to extract company and role from title
            company, title = self._parse_title(raw_title)

            # Extract snippet for description
            snippet_elem = (
                result.find("div", class_=re.compile(r"VwiC3b"))
                or result.find("span", class_=re.compile(r"aCOpRe|st"))
            )
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            return JobListing(
                company_name=company,
                job_title=title,
                location="India",
                apply_url=url,
                source_platform="google_jobs",
                job_description_summary=snippet[:500],
                company_prestige_score=company.get("priority", False) and 10 or 5,
                estimated_salary_lpa=None,
                company_category=company.get("category"),
            )

        except Exception as e:
            logger.debug(f"[google_jobs] Result parse error: {e}")
            return None

    def _parse_title(self, raw_title: str) -> tuple[str, str]:
        """Extract company and role from search result title."""
        separators = [" - ", " at ", " | ", ": ", " — "]

        for sep in separators:
            if sep in raw_title:
                parts = raw_title.split(sep, 1)
                if len(parts) == 2:
                    return parts[1].strip(), parts[0].strip()

        return "Unknown", raw_title
