"""
SmartRecruiters ATS Scraper.
"""
from scrapers.base_scraper import BaseScraper
from core.models import JobListing

class SmartRecruitersScraper(BaseScraper):
    def __init__(self, session, semaphore):
        super().__init__("SmartRecruiters", session, semaphore)

    async def scrape(self, company_config) -> list[JobListing]:
        company_id = company_config.get("ats_url")
        if not company_id:
            return []

        api_url = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
        
        data = await self._get_json(api_url)
        if not data or not isinstance(data, dict):
            return []

        jobs = []
        for job_data in data.get("content", []):
            loc_data = job_data.get("location", {})
            loc = f"{loc_data.get('city', '')}, {loc_data.get('region', '')}, {loc_data.get('country', '')}"
            title = job_data.get("name", "")
            
            job = JobListing(
                company_name=company_config["name"],
                job_title=title,
                location=loc,
                apply_url=f"https://careers.smartrecruiters.com/{company_id}/{job_data.get('id')}",
                source_platform="smartrecruiters",
                ats_provider="smartrecruiters",
                posting_date=job_data.get("releasedDate", ""),
                company_category=company_config.get("category"),
            )
            jobs.append(job)
            
        return jobs
