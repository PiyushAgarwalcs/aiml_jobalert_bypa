"""
Generic career page scraper for companies with custom ATS (not Greenhouse/Lever/etc).
Fully async, works with the V2 ScraperManager.

Strategy:
1. Fetch the career page HTML
2. Extract all <a> links whose text matches AI/ML/SWE title keywords
3. Fall back to structured card selectors (div/li/article with job-related class names)
4. Filter to Bangalore / India / Remote locations only
5. Return JobListings — location & role filtering happens in FilterEngine
"""

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config.search_terms import ATS_TITLE_KEYWORDS
from core.models import JobListing
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Location tokens that indicate an India/Bangalore role
INDIA_LOCATION_TOKENS = re.compile(
    r"bangalore|bengaluru|karnataka|india|remote|pan.india|hyderabad|pune|chennai|"
    r"mumbai|delhi|gurugram|gurgaon|noida|work.from.home|wfh",
    re.IGNORECASE,
)

CARD_SELECTORS = [
    ("div",     re.compile(r"job|position|opening|career|role|listing|posting", re.I)),
    ("li",      re.compile(r"job|position|opening|career|role|listing|posting", re.I)),
    ("article", re.compile(r"job|position|opening|career|role|listing|posting", re.I)),
    ("tr",      re.compile(r"job|position|opening|career|role", re.I)),
]


class CustomCareerScraper(BaseScraper):
    """Async scraper for companies whose career pages use a bespoke/unknown ATS."""

    def __init__(self, session, semaphore):
        super().__init__("custom_career", session, semaphore)

    async def scrape(self, company_config: Dict[str, Any]) -> List[JobListing]:
        career_url = company_config.get("career_url", "")
        if not career_url:
            return []

        company_name = company_config.get("name", "Unknown")
        html = await self._get(career_url)
        if not html:
            logger.debug(f"[custom] No HTML for {company_name}")
            return []

        jobs: List[JobListing] = []
        seen_urls: set = set()

        try:
            soup = BeautifulSoup(html, "lxml")
            jobs.extend(self._extract_from_links(soup, career_url, company_config, seen_urls))
            jobs.extend(self._extract_from_cards(soup, career_url, company_config, seen_urls))
        except Exception as e:
            logger.warning(f"[custom] Parse error for {company_name}: {e}")

        logger.info(f"[custom] {company_name}: {len(jobs)} relevant jobs")
        return jobs

    # ── Strategy 1: anchor tag scan ──────────────────────────────────────────

    def _extract_from_links(
        self,
        soup: BeautifulSoup,
        base_url: str,
        cfg: Dict,
        seen: set,
    ) -> List[JobListing]:
        results = []
        kws = [k.lower() for k in ATS_TITLE_KEYWORDS]

        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 4 or len(text) > 200:
                continue
            text_lower = text.lower()
            if not any(kw in text_lower for kw in kws):
                continue

            href = a["href"]
            url = href if href.startswith("http") else urljoin(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            location = self._find_nearby_location(a) or "India"
            job = self._make_job(text, location, url, cfg)
            if job:
                results.append(job)

        return results

    # ── Strategy 2: card/row scan ─────────────────────────────────────────────

    def _extract_from_cards(
        self,
        soup: BeautifulSoup,
        base_url: str,
        cfg: Dict,
        seen: set,
    ) -> List[JobListing]:
        results = []
        kws = [k.lower() for k in ATS_TITLE_KEYWORDS]

        for tag, cls_pattern in CARD_SELECTORS:
            for card in soup.find_all(tag, class_=cls_pattern):
                title_elem = (
                    card.find("h1") or card.find("h2") or card.find("h3")
                    or card.find("h4") or card.find("strong")
                    or card.find("a", href=True)
                )
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                if not title or not any(kw in title.lower() for kw in kws):
                    continue

                link = card.find("a", href=True)
                if not link:
                    continue
                href = link["href"]
                url = href if href.startswith("http") else urljoin(base_url, href)
                if url in seen:
                    continue
                seen.add(url)

                location = self._find_nearby_location(card) or "India"
                job = self._make_job(title, location, url, cfg)
                if job:
                    results.append(job)

        return results

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_nearby_location(self, elem) -> Optional[str]:
        """Look for a location string near the element (siblings, parent text)."""
        # Check the element's own text and its parent's text for location tokens
        for text in [elem.get_text(" ", strip=True),
                     elem.parent.get_text(" ", strip=True) if elem.parent else ""]:
            m = INDIA_LOCATION_TOKENS.search(text)
            if m:
                # Return a short window around the match
                start = max(0, m.start() - 5)
                end = min(len(text), m.end() + 30)
                return text[start:end].strip()
        return None

    def _make_job(
        self, title: str, location: str, url: str, cfg: Dict
    ) -> Optional[JobListing]:
        if not url or not title:
            return None
        try:
            return JobListing(
                company_name=cfg["name"],
                job_title=title,
                location=location,
                apply_url=url,
                source_platform="custom_career",
                ats_provider="custom",
                company_category=cfg.get("category"),
                company_prestige_score=cfg.get("prestige_score", 6),
                job_description_summary=f"Career page listing | {cfg['name']} | {title}",
            )
        except Exception:
            return None
