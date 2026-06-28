"""
Wellfound (AngelList Talent) scraper for the AI/ML Job Alert System.
Uses Wellfound's GraphQL API and embedded JSON data extraction.
"""

import json
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from core.models import JobListing
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

WELLFOUND_BASE_URL = "https://wellfound.com"
WELLFOUND_GRAPHQL_URL = "https://wellfound.com/graphql"


class WellfoundScraper(BaseScraper):
    """Scrapes Wellfound for AI/ML jobs using GraphQL API."""

    def __init__(self):
        super().__init__("wellfound", session, semaphore)

    def scrape(self) -> list[JobListing]:
        """Search Wellfound for AI/ML jobs."""
        all_jobs = []

        # Strategy 1: Try GraphQL API queries
        graphql_jobs = self._search_graphql()
        if graphql_jobs:
            all_jobs.extend(graphql_jobs)
            return all_jobs

        # Strategy 2: Try role search pages with better headers
        search_paths = [
            "/role/l/machine-learning-engineer/india",
            "/role/l/data-scientist/india",
            "/role/l/artificial-intelligence-engineer/india",
        ]

        for path in search_paths:
            try:
                self._rotate_user_agent()
                url = f"{WELLFOUND_BASE_URL}{path}"
                headers = {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Referer": "https://wellfound.com/",
                    "DNT": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                }
                response = self._get(url, headers=headers)
                if response is None:
                    continue

                jobs = self._parse_results(response.text)
                all_jobs.extend(jobs)

            except Exception as e:
                logger.warning(f"[wellfound] Failed path '{path}': {e}")
                continue

        return all_jobs

    def _search_graphql(self) -> list[JobListing]:
        """Try to search via Wellfound's GraphQL API."""
        jobs = []

        # GraphQL query for job search
        query = """
        query JobSearchQuery($query: String!, $page: Int, $location: String) {
            talent {
                jobListings(query: $query, page: $page, locationName: $location) {
                    results {
                        id
                        title
                        slug
                        company {
                            name
                            slug
                        }
                        remotePolicy
                        liveStartAt
                        compensation {
                            min
                            max
                            currency
                        }
                        locationNames
                    }
                }
            }
        }
        """

        search_terms = [
            "machine learning",
            "artificial intelligence",
            "data scientist",
        ]

        for term in search_terms:
            try:
                payload = {
                    "operationName": "JobSearchQuery",
                    "query": query,
                    "variables": {
                        "query": term,
                        "page": 1,
                        "location": "India",
                    },
                }

                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Origin": "https://wellfound.com",
                    "Referer": "https://wellfound.com/",
                    "X-Requested-With": "XMLHttpRequest",
                }

                response = self._post(WELLFOUND_GRAPHQL_URL, headers=headers, json_data=payload)
                if response is None:
                    continue

                data = response.json()
                results = (
                    data.get("data", {})
                    .get("talent", {})
                    .get("jobListings", {})
                    .get("results", [])
                )

                for item in results:
                    job = self._parse_graphql_result(item)
                    if job:
                        jobs.append(job)

            except Exception as e:
                logger.debug(f"[wellfound] GraphQL query failed for '{term}': {e}")
                continue

        return jobs

    def _parse_graphql_result(self, item: dict) -> Optional[JobListing]:
        """Parse a single GraphQL result."""
        try:
            title = item.get("title", "").strip()
            company_data = item.get("company", {})
            company_name = company_data.get("name", "Unknown Startup")
            company_slug = company_data.get("slug", "")

            locations = item.get("locationNames", [])
            location = ", ".join(locations) if locations else "Remote"

            slug = item.get("slug", "")
            apply_url = f"{WELLFOUND_BASE_URL}/jobs/{slug}" if slug else ""
            if not apply_url and company_slug:
                apply_url = f"{WELLFOUND_BASE_URL}/company/{company_slug}"

            # Compensation
            compensation = item.get("compensation", {}) or {}
            salary = None
            if compensation.get("min") and compensation.get("max"):
                salary = f"{compensation['currency']} {compensation['min']}-{compensation['max']}"

            if title and company_name:
                return JobListing(
                    company_name=company_name,
                    job_title=title,
                    location=location,
                    apply_url=apply_url,
                    source_platform="wellfound",
                    salary=salary,
                    company_prestige_score=company.get("priority", False) and 10 or 5,
                    estimated_salary_lpa=None,
                    company_category=company.get("category"),
                )

        except Exception as e:
            logger.debug(f"[wellfound] GraphQL result parse error: {e}")

        return None

    def _parse_results(self, html: str) -> list[JobListing]:
        """Parse Wellfound job listing page (HTML + embedded JSON)."""
        jobs = []

        try:
            soup = BeautifulSoup(html, "lxml")

            # Strategy 1: Extract from __NEXT_DATA__ script tag
            next_data = soup.find("script", {"id": "__NEXT_DATA__"})
            if next_data:
                try:
                    data = json.loads(next_data.string or "")
                    parsed = self._parse_next_data(data)
                    if parsed:
                        jobs.extend(parsed)
                        return jobs
                except (json.JSONDecodeError, TypeError):
                    pass

            # Strategy 2: Try script tags with embedded JSON
            scripts = soup.find_all("script", type="application/json")
            for script in scripts:
                try:
                    data = json.loads(script.string or "")
                    parsed = self._parse_next_data(data)
                    if parsed:
                        jobs.extend(parsed)
                except (json.JSONDecodeError, TypeError):
                    continue

            # Strategy 3: Parse DOM cards
            job_cards = soup.find_all("div", attrs={"class": re.compile(r"styles_result|jobListingCard")})
            for card in job_cards:
                job = self._parse_card(card)
                if job:
                    jobs.append(job)

        except Exception as e:
            logger.warning(f"[wellfound] Parse error: {e}")

        return jobs

    def _parse_next_data(self, data: dict) -> list[JobListing]:
        """Parse __NEXT_DATA__ JSON structure."""
        jobs = []
        try:
            if not isinstance(data, dict):
                return jobs

            props = data.get("props", {}).get("pageProps", {})

            # Try various keys
            listings = (
                props.get("listings", [])
                or props.get("jobs", [])
                or props.get("jobListings", {}).get("results", [])
                or props.get("initialData", {}).get("results", [])
            )

            for item in listings:
                if not isinstance(item, dict):
                    continue

                title = item.get("title", "")
                company_name = (
                    item.get("companyName", "")
                    or item.get("company", {}).get("name", "")
                    if isinstance(item.get("company"), dict) else ""
                )
                location = item.get("location", "Remote")
                if isinstance(location, list):
                    location = ", ".join(location)

                slug = item.get("slug", "")
                apply_url = f"{WELLFOUND_BASE_URL}/jobs/{slug}" if slug else ""
                salary = item.get("salary", None)

                if title and company_name:
                    jobs.append(JobListing(
                        company_name=company_name,
                        job_title=title,
                        location=str(location),
                        apply_url=apply_url,
                        source_platform="wellfound",
                        salary=salary if isinstance(salary, str) else None,
                        company_prestige_score=company.get("priority", False) and 10 or 5,
                        estimated_salary_lpa=None,
                        company_category=company.get("category"),
                    ))

        except Exception as e:
            logger.debug(f"[wellfound] Next.js data parse error: {e}")

        return jobs

    def _parse_card(self, card) -> Optional[JobListing]:
        """Parse a single Wellfound job card."""
        try:
            title_elem = card.find("a", attrs={"class": re.compile(r"title")})
            if not title_elem:
                title_elem = card.find("h4") or card.find("a")
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            apply_url = title_elem.get("href", "")
            if apply_url and not apply_url.startswith("http"):
                apply_url = f"{WELLFOUND_BASE_URL}{apply_url}"

            company_elem = card.find("h2") or card.find("a", attrs={"class": re.compile(r"company")})
            company = company_elem.get_text(strip=True) if company_elem else "Unknown Startup"

            location_elem = card.find("span", attrs={"class": re.compile(r"location")})
            location = location_elem.get_text(strip=True) if location_elem else "Remote"

            salary_elem = card.find("span", attrs={"class": re.compile(r"salary")})
            salary = salary_elem.get_text(strip=True) if salary_elem else None

            return JobListing(
                company_name=company,
                job_title=title,
                location=location,
                apply_url=apply_url,
                source_platform="wellfound",
                salary=salary,
                company_prestige_score=company.get("priority", False) and 10 or 5,
                estimated_salary_lpa=None,
                company_category=company.get("category"),
            )

        except Exception as e:
            logger.debug(f"[wellfound] Card parse error: {e}")
            return None
