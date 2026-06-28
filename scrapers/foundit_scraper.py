"""
Foundit.in (formerly Monster India) scraper for the AI/ML Job Alert System.
Uses Foundit's search page with HTML parsing and API fallback.
"""

import json
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from core.models import JobListing
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

FOUNDIT_BASE_URL = "https://www.foundit.in"


class FounditScraper(BaseScraper):
    """Scrapes Foundit.in for AI/ML fresher jobs."""

    def __init__(self):
        super().__init__("foundit", session, semaphore)

    def scrape(self) -> list[JobListing]:
        """Search Foundit for AI/ML fresher jobs."""
        all_jobs = []

        queries = [
            "machine-learning",
            "artificial-intelligence",
            "data-scientist",
            "AI-engineer",
        ]

        for query in queries:
            try:
                jobs = self._search_jobs(query)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.warning(f"[foundit] Failed query '{query}': {e}")
                continue

        return all_jobs

    def _search_jobs(self, query: str) -> list[JobListing]:
        """Search Foundit using the HTML search page."""
        # Use the HTML search URL directly (API endpoint was unreliable)
        url = f"{FOUNDIT_BASE_URL}/srp/results"
        params = {
            "searchId": "",
            "query": query.replace("-", " "),
            "locations": "Bangalore",
            "experienceRanges": "0~1",
            "sort": "1",  # Sort by recency
            "limit": "20",
            "offset": "0",
        }

        self._rotate_user_agent()
        response = self._get(url, params=params)
        if response is None:
            # Fallback: try the direct URL pattern
            return self._scrape_direct_url(query)

        return self._parse_html_results(response.text)

    def _scrape_direct_url(self, query: str) -> list[JobListing]:
        """Fallback: try direct URL pattern for Foundit."""
        url = f"{FOUNDIT_BASE_URL}/{query}-jobs-in-bangalore"
        params = {"experience": "0", "sort": "1"}

        response = self._get(url, params=params)
        if response is None:
            return []

        return self._parse_html_results(response.text)

    def _parse_html_results(self, html: str) -> list[JobListing]:
        """Parse Foundit HTML search results."""
        jobs = []

        try:
            soup = BeautifulSoup(html, "lxml")

            # Strategy 1: Try embedded JSON data (Next.js / SSR)
            scripts = soup.find_all("script", {"id": "__NEXT_DATA__"})
            if not scripts:
                scripts = soup.find_all("script", type="application/json")

            for script in scripts:
                try:
                    data = json.loads(script.string or "")
                    parsed = self._extract_jobs_from_json(data)
                    if parsed:
                        jobs.extend(parsed)
                        return jobs
                except (json.JSONDecodeError, TypeError):
                    continue

            # Strategy 2: Parse job card DOM elements
            job_cards = soup.find_all("div", class_=re.compile(
                r"card-apply-content|jobTuple|srpResultCardContainer|jobCard"
            ))

            if not job_cards:
                # Try more generic selectors
                job_cards = soup.find_all("div", attrs={"data-job-id": True})

            for card in job_cards:
                job = self._parse_html_card(card)
                if job:
                    jobs.append(job)

        except Exception as e:
            logger.warning(f"[foundit] HTML parsing error: {e}")

        return jobs

    def _extract_jobs_from_json(self, data: dict) -> list[JobListing]:
        """Extract jobs from embedded JSON data."""
        jobs = []

        try:
            # Navigate Next.js data structure
            if isinstance(data, dict):
                page_props = data.get("props", {}).get("pageProps", {})
                search_results = (
                    page_props.get("searchResults", [])
                    or page_props.get("initialSearchResults", {}).get("searchResults", [])
                    or page_props.get("jobDetails", [])
                )

                for item in search_results:
                    if not isinstance(item, dict):
                        continue

                    title = item.get("title", "").strip()
                    company = item.get("companyName", "Unknown").strip()
                    location = item.get("locations", "India")
                    if isinstance(location, list):
                        location = ", ".join(location)

                    apply_url = item.get("jobUrl", "") or item.get("detailUrl", "")
                    if apply_url and not apply_url.startswith("http"):
                        apply_url = f"{FOUNDIT_BASE_URL}{apply_url}"

                    salary = item.get("salary", None)
                    if isinstance(salary, dict):
                        salary = salary.get("label", None)

                    experience = item.get("experience", "")
                    if isinstance(experience, dict):
                        experience = experience.get("label", "")

                    skills = item.get("skills", [])
                    posted_date = item.get("postedDate", "")

                    if title and company:
                        jobs.append(JobListing(
                            company_name=company,
                            job_title=title,
                            location=str(location),
                            apply_url=apply_url,
                            source_platform="foundit",
                            salary=salary if isinstance(salary, str) else None,
                            experience_required=str(experience),
                            required_skills=skills if isinstance(skills, list) else [],
                            posting_date=posted_date if posted_date else None,
                            company_prestige_score=company.get("priority", False) and 10 or 5,
                            estimated_salary_lpa=None,
                            company_category=company.get("category"),
                        ))

        except Exception as e:
            logger.debug(f"[foundit] JSON extraction error: {e}")

        return jobs

    def _parse_html_card(self, card) -> Optional[JobListing]:
        """Parse a single Foundit HTML job card."""
        try:
            title_elem = card.find("a", class_=re.compile(r"title|jobTitle|cardTitle"))
            if not title_elem:
                title_elem = card.find("h3") or card.find("h2")
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            apply_url = ""
            if hasattr(title_elem, "get"):
                apply_url = title_elem.get("href", "")
            if apply_url and not apply_url.startswith("http"):
                apply_url = f"{FOUNDIT_BASE_URL}{apply_url}"

            company_elem = card.find("span", class_=re.compile(r"company|companyName"))
            if not company_elem:
                company_elem = card.find("a", class_=re.compile(r"company"))
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"

            location_elem = card.find("span", class_=re.compile(r"loc|location"))
            location = location_elem.get_text(strip=True) if location_elem else "India"

            salary_elem = card.find("span", class_=re.compile(r"sal|salary"))
            salary = salary_elem.get_text(strip=True) if salary_elem else None

            if not apply_url:
                return None

            return JobListing(
                company_name=company,
                job_title=title,
                location=location,
                apply_url=apply_url,
                source_platform="foundit",
                salary=salary,
                company_prestige_score=company.get("priority", False) and 10 or 5,
                estimated_salary_lpa=None,
                company_category=company.get("category"),
            )

        except Exception as e:
            logger.debug(f"[foundit] Card parse error: {e}")
            return None
