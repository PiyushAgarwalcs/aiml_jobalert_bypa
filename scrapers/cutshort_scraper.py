"""
CutShort scraper for the AI/ML Job Alert System.
Scrapes CutShort job listings using their public search endpoints.
"""

import json
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from core.models import JobListing
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

CUTSHORT_BASE_URL = "https://cutshort.io"


class CutShortScraper(BaseScraper):
    """Scrapes CutShort for AI/ML fresher jobs."""

    def __init__(self):
        super().__init__("cutshort", session, semaphore)

    def scrape(self) -> list[JobListing]:
        """Search CutShort for AI/ML fresher jobs."""
        all_jobs = []

        search_paths = [
            "/jobs/machine-learning/in-bangalore-experience-0-1",
            "/jobs/artificial-intelligence/in-bangalore-experience-0-1",
            "/jobs/data-science/in-bangalore-experience-0-1",
            "/jobs/deep-learning/in-bangalore-experience-0-1",
            "/jobs/python-machine-learning/in-bangalore-experience-0-1",
            "/jobs/nlp/in-bangalore-experience-0-1",
        ]

        for path in search_paths:
            try:
                self._rotate_user_agent()
                url = f"{CUTSHORT_BASE_URL}{path}"

                headers = {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": f"{CUTSHORT_BASE_URL}/",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                }

                response = self._get(url, headers=headers)
                if response is None:
                    continue

                jobs = self._parse_results(response.text)
                all_jobs.extend(jobs)

            except Exception as e:
                logger.warning(f"[cutshort] Failed path '{path}': {e}")
                continue

        return all_jobs

    def _parse_results(self, html: str) -> list[JobListing]:
        """Parse CutShort search results page."""
        jobs = []

        try:
            soup = BeautifulSoup(html, "lxml")

            # Strategy 1: Extract from embedded JSON (__NEXT_DATA__ or similar)
            next_data = soup.find("script", {"id": "__NEXT_DATA__"})
            if next_data:
                try:
                    data = json.loads(next_data.string or "")
                    parsed = self._extract_from_json(data)
                    if parsed:
                        jobs.extend(parsed)
                        return jobs
                except (json.JSONDecodeError, TypeError):
                    pass

            # Strategy 2: Parse job cards from DOM
            job_cards = soup.find_all("div", attrs={
                "class": re.compile(r"job-card|jobCard|listing-card|search-result", re.I)
            })

            if not job_cards:
                # Try link-based approach
                all_links = soup.find_all("a", href=re.compile(r"/job/|/jobs/"))
                seen_urls = set()
                for link in all_links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    # Skip navigation/category links
                    if len(text) < 10 or len(text) > 200:
                        continue
                    if href in seen_urls:
                        continue

                    seen_urls.add(href)
                    job = self._create_job_from_link(text, href)
                    if job:
                        jobs.append(job)
            else:
                for card in job_cards:
                    job = self._parse_card(card)
                    if job:
                        jobs.append(job)

        except Exception as e:
            logger.warning(f"[cutshort] Parse error: {e}")

        return jobs

    def _extract_from_json(self, data: dict) -> list[JobListing]:
        """Extract jobs from embedded JSON data."""
        jobs = []
        try:
            props = data.get("props", {}).get("pageProps", {})
            job_list = (
                props.get("jobs", [])
                or props.get("listings", [])
                or props.get("results", [])
                or props.get("searchResults", [])
            )

            for item in job_list:
                if not isinstance(item, dict):
                    continue

                title = item.get("title", "").strip()
                company = (
                    item.get("companyName", "")
                    or item.get("company", {}).get("name", "") if isinstance(item.get("company"), dict) else ""
                )
                location = item.get("location", "Bangalore")
                if isinstance(location, list):
                    location = ", ".join(location)

                slug = item.get("slug", "") or item.get("id", "")
                apply_url = f"{CUTSHORT_BASE_URL}/job/{slug}" if slug else ""

                salary = item.get("salary", None) or item.get("ctc", None)
                if isinstance(salary, dict):
                    salary = f"{salary.get('min', '')}-{salary.get('max', '')} LPA"
                elif isinstance(salary, (int, float)):
                    salary = f"₹{salary} LPA"

                experience = item.get("experience", "")
                skills = item.get("skills", []) or item.get("tags", [])
                if isinstance(skills, list):
                    skills = [str(s.get("name", s)) if isinstance(s, dict) else str(s) for s in skills]

                if title and company:
                    jobs.append(JobListing(
                        company_name=str(company),
                        job_title=title,
                        location=str(location),
                        apply_url=apply_url,
                        source_platform="cutshort",
                        salary=str(salary) if salary else None,
                        experience_required=str(experience),
                        required_skills=skills,
                        company_prestige_score=get_prestige_score(str(company)),
                        estimated_salary_lpa=get_estimated_salary(str(company)),
                        company_category=company.get("category")),
                    ))

        except Exception as e:
            logger.debug(f"[cutshort] JSON extraction error: {e}")

        return jobs

    def _parse_card(self, card) -> Optional[JobListing]:
        """Parse a single CutShort job card."""
        try:
            title_elem = card.find("h3") or card.find("h2") or card.find("a", href=re.compile(r"/job/"))
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)

            link = card.find("a", href=True)
            apply_url = ""
            if link:
                apply_url = link.get("href", "")
                if apply_url and not apply_url.startswith("http"):
                    apply_url = f"{CUTSHORT_BASE_URL}{apply_url}"

            company_elem = card.find("p", class_=re.compile(r"company")) or card.find("span", class_=re.compile(r"company"))
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"

            location_elem = card.find("span", class_=re.compile(r"location|city"))
            location = location_elem.get_text(strip=True) if location_elem else "Bangalore"

            salary_elem = card.find("span", class_=re.compile(r"salary|ctc|compensation"))
            salary = salary_elem.get_text(strip=True) if salary_elem else None

            if not apply_url:
                return None

            return JobListing(
                company_name=company,
                job_title=title,
                location=location,
                apply_url=apply_url,
                source_platform="cutshort",
                salary=salary,
                company_prestige_score=company.get("priority", False) and 10 or 5,
                estimated_salary_lpa=None,
                company_category=company.get("category"),
            )

        except Exception as e:
            logger.debug(f"[cutshort] Card parse error: {e}")
            return None

    def _create_job_from_link(self, text: str, href: str) -> Optional[JobListing]:
        """Create a job listing from a link element."""
        try:
            apply_url = href
            if not apply_url.startswith("http"):
                apply_url = f"{CUTSHORT_BASE_URL}{href}"

            # Try to extract company from the text
            parts = re.split(r" at | - | \| ", text, maxsplit=1)
            if len(parts) == 2:
                title, company = parts[0].strip(), parts[1].strip()
            else:
                title = text.strip()
                company = "Unknown"

            return JobListing(
                company_name=company,
                job_title=title,
                location="Bangalore",
                apply_url=apply_url,
                source_platform="cutshort",
                company_prestige_score=company.get("priority", False) and 10 or 5,
                estimated_salary_lpa=None,
                company_category=company.get("category"),
            )

        except Exception as e:
            logger.debug(f"[cutshort] Link parse error: {e}")
            return None
