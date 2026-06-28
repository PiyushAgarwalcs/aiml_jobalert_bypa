"""
Naukri.com scraper for the AI/ML Job Alert System.
Uses Naukri's internal search API and HTML fallback for fresher AI/ML positions.
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

NAUKRI_API_URL = "https://www.naukri.com/jobapi/v3/search"
NAUKRI_HTML_BASE = "https://www.naukri.com"


class NaukriScraper(BaseScraper):
    """Scrapes Naukri.com for AI/ML fresher jobs."""

    def __init__(self):
        super().__init__("naukri", session, semaphore)

    def scrape(self) -> list[JobListing]:
        """Search Naukri for AI/ML fresher jobs."""
        all_jobs = []

        queries = [
            "machine learning",
            "artificial intelligence",
            "data scientist",
            "AI engineer",
            "deep learning",
            "NLP engineer",
            "generative AI",
        ]

        for query in queries:
            try:
                # Try API first, then HTML fallback
                jobs = self._search_api(query)
                if not jobs:
                    jobs = self._scrape_html(query)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.warning(f"[naukri] Failed query '{query}': {e}")
                continue

        return all_jobs

    def _search_api(self, query: str) -> list[JobListing]:
        """Search Naukri API for a specific query."""
        params = {
            "noOfResults": "20",
            "urlType": "search_by_keyword",
            "searchType": "adv",
            "keyword": query,
            "pageNo": "1",
            "experience": "0",
            "sort": "date",
            "location": "bangalore",
            "seoKey": f"{query.replace(' ', '-')}-jobs-in-bangalore",
            "src": "jobsearchDesk",
            "latLong": "",
        }

        # Naukri API requires these specific headers to avoid 406
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"https://www.naukri.com/{query.replace(' ', '-')}-jobs-in-bangalore?experience=0",
            "appid": "109",
            "systemid": "Starter",
            "gid": "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
            "Content-Type": "application/json",
            "clientid": "d3skt0p",
            "Connection": "keep-alive",
        }

        response = self._get(NAUKRI_API_URL, headers=headers, params=params)
        if response is None:
            return []

        try:
            data = response.json()
            return self._parse_api_results(data)
        except (ValueError, KeyError) as e:
            logger.debug(f"[naukri] API JSON parse failed: {e}")
            return []

    def _parse_api_results(self, data: dict) -> list[JobListing]:
        """Parse Naukri API JSON response."""
        jobs = []

        job_details = data.get("jobDetails", [])
        for item in job_details:
            try:
                title = item.get("title", "").strip()
                company = item.get("companyName", "Unknown").strip()
                placeholders = item.get("placeholders", [])

                # Extract location from placeholders
                loc_str = "India"
                exp_str = ""
                salary_str = ""
                for placeholder in placeholders:
                    ptype = placeholder.get("type", "")
                    plabel = placeholder.get("label", "")
                    if ptype == "location":
                        loc_str = plabel
                    elif ptype == "experience":
                        exp_str = plabel
                    elif ptype == "salary":
                        salary_str = plabel

                apply_url = item.get("jdURL", "")
                if apply_url and not apply_url.startswith("http"):
                    apply_url = f"https://www.naukri.com{apply_url}"

                # Tags / skills
                tags = item.get("tagsAndSkills", "")
                skills = [s.strip() for s in tags.split(",")] if tags else []

                # Created date
                created_date = item.get("createdDate", "")

                # Job description snippet
                job_desc = item.get("jobDescription", "")

                job = JobListing(
                    company_name=company,
                    job_title=title,
                    location=loc_str,
                    apply_url=apply_url,
                    source_platform="naukri",
                    salary=salary_str if salary_str else None,
                    experience_required=exp_str,
                    required_skills=skills,
                    posting_date=created_date if created_date else None,
                    job_description_summary=job_desc[:500] if job_desc else None,
                    company_prestige_score=company.get("priority", False) and 10 or 5,
                    estimated_salary_lpa=None,
                    company_category=company.get("category"),
                    salary_confidence="low" if get_estimated_salary(company) else None,
                )
                jobs.append(job)

            except Exception as e:
                logger.debug(f"[naukri] Error parsing job: {e}")
                continue

        return jobs

    def _scrape_html(self, query: str) -> list[JobListing]:
        """Fallback: scrape Naukri HTML search results."""
        encoded_query = query.replace(" ", "-")
        url = f"https://www.naukri.com/{encoded_query}-jobs-in-bangalore?experience=0"

        # Rotate user-agent for HTML requests
        self._rotate_user_agent()

        response = self._get(url)
        if response is None:
            return []

        jobs = []
        try:
            soup = BeautifulSoup(response.text, "lxml")

            # Try to find embedded JSON data (Next.js / SSR data)
            scripts = soup.find_all("script", type="application/json")
            for script in scripts:
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict) and "jobDetails" in str(data)[:1000]:
                        parsed = self._parse_api_results(data)
                        if parsed:
                            jobs.extend(parsed)
                            return jobs
                except (json.JSONDecodeError, TypeError):
                    continue

            # Fallback: parse DOM structure
            job_cards = soup.find_all("article", class_="jobTuple")
            if not job_cards:
                job_cards = soup.find_all("div", attrs={"class": re.compile(r"srp-jobtuple|cust-job-tuple")})

            for card in job_cards:
                job = self._parse_html_card(card)
                if job:
                    jobs.append(job)

        except Exception as e:
            logger.warning(f"[naukri] HTML parsing error: {e}")

        return jobs

    def _parse_html_card(self, card) -> Optional[JobListing]:
        """Parse a single Naukri HTML job card."""
        try:
            title_elem = (
                card.find("a", class_="title")
                or card.find("a", class_=re.compile(r"title"))
                or card.find("a", attrs={"class": re.compile(r"jobTitle")})
            )
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            apply_url = title_elem.get("href", "")

            company_elem = (
                card.find("a", class_="subTitle")
                or card.find("a", class_=re.compile(r"comp-name|companyName"))
            )
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"

            location_elem = (
                card.find("li", class_="location")
                or card.find("span", class_=re.compile(r"loc|location|ni-job-tuple-icon-srp-location"))
            )
            location = location_elem.get_text(strip=True) if location_elem else "India"

            exp_elem = (
                card.find("li", class_="experience")
                or card.find("span", class_=re.compile(r"exp|experience|ni-job-tuple-icon-srp-experience"))
            )
            experience = exp_elem.get_text(strip=True) if exp_elem else ""

            salary_elem = (
                card.find("li", class_="salary")
                or card.find("span", class_=re.compile(r"sal|salary|ni-job-tuple-icon-srp-rupee"))
            )
            salary = salary_elem.get_text(strip=True) if salary_elem else None

            return JobListing(
                company_name=company,
                job_title=title,
                location=location,
                apply_url=apply_url,
                source_platform="naukri",
                salary=salary,
                experience_required=experience,
                company_prestige_score=company.get("priority", False) and 10 or 5,
                estimated_salary_lpa=None,
                company_category=company.get("category"),
            )

        except Exception as e:
            logger.debug(f"[naukri] Error parsing HTML card: {e}")
            return None
