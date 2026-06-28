"""
Company database with ATS platform info, career page URLs, prestige scores,
and category classification for the AI/ML Job Alert System.

Board tokens verified 2026-06 against live API responses.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CompanyInfo:
    """Metadata for a target company."""
    name: str
    category: str
    prestige_score: int                    # 1-10
    ats_platform: Optional[str] = None     # 'greenhouse', 'lever', 'workday', 'custom', None
    ats_board_token: Optional[str] = None  # Board identifier for Greenhouse/Lever
    careers_url: Optional[str] = None      # Fallback careers page URL
    estimated_salary_lpa: Optional[int] = None  # Estimated fresher salary in LPA


# ─── Complete Company Database ─────────────────────────────────────────────────

COMPANIES: list[CompanyInfo] = [
    # ═══════════════════════════════════════════════════════════════════════════
    # BIG TECH (Prestige 9-10)
    # ═══════════════════════════════════════════════════════════════════════════
    CompanyInfo(
        name="Google", category="Big Tech", prestige_score=10,
        ats_platform="custom",
        careers_url="https://www.google.com/about/careers/applications/jobs/results/?location=India&q=machine%20learning",
        estimated_salary_lpa=30,
    ),
    CompanyInfo(
        name="Microsoft", category="Big Tech", prestige_score=10,
        ats_platform="custom",
        careers_url="https://careers.microsoft.com/us/en/search-results?keywords=machine%20learning&country=India",
        estimated_salary_lpa=28,
    ),
    CompanyInfo(
        name="Amazon", category="Big Tech", prestige_score=9,
        ats_platform="custom",
        careers_url="https://www.amazon.jobs/en/search?base_query=machine+learning&loc_query=India",
        estimated_salary_lpa=28,
    ),
    CompanyInfo(
        name="NVIDIA", category="Big Tech", prestige_score=10,
        ats_platform="custom",
        careers_url="https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        estimated_salary_lpa=30,
    ),
    CompanyInfo(
        name="Adobe", category="Big Tech", prestige_score=9,
        ats_platform="custom",
        careers_url="https://careers.adobe.com/us/en/search-results?keywords=machine%20learning",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="Salesforce", category="Big Tech", prestige_score=9,
        ats_platform="custom",
        careers_url="https://careers.salesforce.com/en/jobs/?search=machine+learning&country=India",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="Oracle", category="Big Tech", prestige_score=8,
        ats_platform="custom",
        careers_url="https://careers.oracle.com/jobs/#en/sites/jobsearch/requisitions?keyword=machine+learning",
        estimated_salary_lpa=20,
    ),
    CompanyInfo(
        name="Intel", category="Big Tech", prestige_score=8,
        ats_platform="custom",
        careers_url="https://jobs.intel.com/en/search-jobs/machine%20learning/india/",
        estimated_salary_lpa=20,
    ),
    CompanyInfo(
        name="Qualcomm", category="Big Tech", prestige_score=8,
        ats_platform="custom",
        careers_url="https://careers.qualcomm.com/careers?query=machine%20learning&location=India",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Cisco", category="Big Tech", prestige_score=8,
        ats_platform="custom",
        careers_url="https://jobs.cisco.com/jobs/SearchJobs/machine%20learning",
        estimated_salary_lpa=20,
    ),
    CompanyInfo(
        name="IBM", category="Big Tech", prestige_score=7,
        ats_platform="custom",
        careers_url="https://www.ibm.com/careers/search?field_keyword_08%5B0%5D=Machine%20Learning",
        estimated_salary_lpa=15,
    ),
    CompanyInfo(
        name="SAP", category="Big Tech", prestige_score=8,
        ats_platform="custom",
        careers_url="https://jobs.sap.com/search/?q=machine+learning&locationsearch=India",
        estimated_salary_lpa=18,
    ),
    CompanyInfo(
        name="Meta", category="Big Tech", prestige_score=10,
        ats_platform="custom",
        careers_url="https://www.metacareers.com/jobs?q=machine%20learning&location%5B0%5D=India",
        estimated_salary_lpa=35,
    ),
    CompanyInfo(
        name="Apple", category="Big Tech", prestige_score=10,
        ats_platform="custom",
        careers_url="https://jobs.apple.com/en-in/search?search=machine+learning",
        estimated_salary_lpa=30,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # VERIFIED GREENHOUSE COMPANIES (board tokens tested against live API)
    # ═══════════════════════════════════════════════════════════════════════════
    CompanyInfo(
        name="Airbnb", category="Big Tech", prestige_score=9,
        ats_platform="greenhouse",
        ats_board_token="airbnb",
        estimated_salary_lpa=28,
    ),
    CompanyInfo(
        name="Rubrik", category="Product", prestige_score=9,
        ats_platform="greenhouse",
        ats_board_token="rubrik",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="Databricks", category="Product", prestige_score=9,
        ats_platform="greenhouse",
        ats_board_token="databricks",
        estimated_salary_lpa=30,
    ),
    CompanyInfo(
        name="MongoDB", category="Product", prestige_score=8,
        ats_platform="greenhouse",
        ats_board_token="mongodb",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Stripe", category="Product", prestige_score=9,
        ats_platform="greenhouse",
        ats_board_token="stripe",
        estimated_salary_lpa=30,
    ),
    CompanyInfo(
        name="Coinbase", category="Product", prestige_score=8,
        ats_platform="greenhouse",
        ats_board_token="coinbase",
        estimated_salary_lpa=28,
    ),
    CompanyInfo(
        name="Anthropic", category="AI Company", prestige_score=9,
        ats_platform="greenhouse",
        ats_board_token="anthropic",
        estimated_salary_lpa=35,
    ),
    CompanyInfo(
        name="Stability AI", category="AI Company", prestige_score=7,
        ats_platform="greenhouse",
        ats_board_token="stabilityai",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Postman", category="Indian Product", prestige_score=8,
        ats_platform="greenhouse",
        ats_board_token="postman",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="PhonePe", category="Indian Product", prestige_score=8,
        ats_platform="greenhouse",
        ats_board_token="phonepe",
        estimated_salary_lpa=20,
    ),
    CompanyInfo(
        name="Notion", category="Product", prestige_score=9,
        ats_platform="custom",
        careers_url="https://www.notion.so/careers",
        estimated_salary_lpa=28,
    ),
    CompanyInfo(
        name="Figma", category="Product", prestige_score=9,
        ats_platform="greenhouse",
        ats_board_token="figma",
        estimated_salary_lpa=28,
    ),
    CompanyInfo(
        name="Discord", category="Product", prestige_score=8,
        ats_platform="greenhouse",
        ats_board_token="discord",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="Cloudflare", category="Product", prestige_score=8,
        ats_platform="greenhouse",
        ats_board_token="cloudflare",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="Zscaler", category="Product", prestige_score=8,
        ats_platform="greenhouse",
        ats_board_token="zscaler",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Nutanix", category="Product", prestige_score=8,
        ats_platform="custom",
        careers_url="https://www.nutanix.com/careers",
        estimated_salary_lpa=20,
    ),
    CompanyInfo(
        name="DoorDash", category="Product", prestige_score=8,
        ats_platform="custom",
        careers_url="https://careers.doordash.com/",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="Pinterest", category="Product", prestige_score=8,
        ats_platform="greenhouse",
        ats_board_token="pinterest",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="Ramp", category="Startup", prestige_score=8,
        ats_platform="custom",
        careers_url="https://ramp.com/careers",
        estimated_salary_lpa=25,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # VERIFIED LEVER COMPANIES (board tokens tested against live API)
    # ═══════════════════════════════════════════════════════════════════════════
    CompanyInfo(
        name="Meesho", category="Indian Product", prestige_score=7,
        ats_platform="lever",
        ats_board_token="meesho",
        estimated_salary_lpa=18,
    ),
    CompanyInfo(
        name="CRED", category="Indian Product", prestige_score=8,
        ats_platform="lever",
        ats_board_token="cred",
        estimated_salary_lpa=22,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPANIES MOVED FROM BROKEN ATS → CUSTOM CAREER PAGES
    # (These returned 404 on Greenhouse/Lever — scrape career pages instead)
    # ═══════════════════════════════════════════════════════════════════════════
    CompanyInfo(
        name="Atlassian", category="Big Tech", prestige_score=9,
        ats_platform="custom",
        careers_url="https://www.atlassian.com/company/careers/all-jobs?search=machine+learning&location=India",
        estimated_salary_lpa=28,
    ),
    CompanyInfo(
        name="Uber", category="Big Tech", prestige_score=9,
        ats_platform="custom",
        careers_url="https://www.uber.com/global/en/careers/list/?query=machine%20learning&location=IND-Bangalore",
        estimated_salary_lpa=28,
    ),
    CompanyInfo(
        name="Snowflake", category="Product", prestige_score=9,
        ats_platform="custom",
        careers_url="https://careers.snowflake.com/us/en/search-results?keywords=machine%20learning",
        estimated_salary_lpa=28,
    ),
    CompanyInfo(
        name="OpenAI", category="AI Company", prestige_score=10,
        ats_platform="custom",
        careers_url="https://openai.com/careers/search/",
        estimated_salary_lpa=35,
    ),
    CompanyInfo(
        name="Scale AI", category="AI Company", prestige_score=8,
        ats_platform="custom",
        careers_url="https://scale.com/careers",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="Hugging Face", category="AI Company", prestige_score=8,
        ats_platform="custom",
        careers_url="https://apply.workable.com/huggingface/",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="ServiceNow", category="Product", prestige_score=8,
        ats_platform="custom",
        careers_url="https://careers.servicenow.com/en/jobs/?q=machine+learning&location=India",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Confluent", category="Product", prestige_score=8,
        ats_platform="custom",
        careers_url="https://careers.confluent.io/search/jobs?q=machine+learning",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="CrowdStrike", category="Product", prestige_score=8,
        ats_platform="custom",
        careers_url="https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Palo Alto Networks", category="Product", prestige_score=8,
        ats_platform="custom",
        careers_url="https://jobs.paloaltonetworks.com/en/jobs/?q=machine+learning",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Cohere", category="AI Company", prestige_score=8,
        ats_platform="custom",
        careers_url="https://cohere.com/careers",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="Perplexity", category="AI Company", prestige_score=8,
        ats_platform="custom",
        careers_url="https://www.perplexity.ai/hub/careers",
        estimated_salary_lpa=28,
    ),
    CompanyInfo(
        name="Mistral AI", category="AI Company", prestige_score=8,
        ats_platform="custom",
        careers_url="https://mistral.ai/careers/",
        estimated_salary_lpa=28,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # AI COMPANIES (Prestige 7-10)
    # ═══════════════════════════════════════════════════════════════════════════
    CompanyInfo(
        name="DeepMind", category="AI Company", prestige_score=10,
        ats_platform="custom",
        careers_url="https://deepmind.google/about/careers/",
        estimated_salary_lpa=35,
    ),
    CompanyInfo(
        name="Weights & Biases", category="AI Company", prestige_score=8,
        ats_platform="custom",
        careers_url="https://boards.greenhouse.io/wandb",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Labelbox", category="AI Company", prestige_score=7,
        ats_platform="custom",
        careers_url="https://labelbox.com/careers/",
        estimated_salary_lpa=20,
    ),
    CompanyInfo(
        name="Turing", category="AI Company", prestige_score=7,
        ats_platform="custom",
        careers_url="https://www.turing.com/careers",
        estimated_salary_lpa=18,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # INDIAN AI COMPANIES (Prestige 6-8)
    # ═══════════════════════════════════════════════════════════════════════════
    CompanyInfo(
        name="Sarvam AI", category="Indian AI", prestige_score=7,
        ats_platform="custom",
        careers_url="https://www.sarvam.ai/careers",
        estimated_salary_lpa=15,
    ),
    CompanyInfo(
        name="Krutrim", category="Indian AI", prestige_score=7,
        ats_platform="custom",
        careers_url="https://www.olakrutrim.com/careers",
        estimated_salary_lpa=15,
    ),
    CompanyInfo(
        name="Fractal Analytics", category="Indian AI", prestige_score=8,
        ats_platform="custom",
        careers_url="https://fractal.ai/careers/",
        estimated_salary_lpa=14,
    ),
    CompanyInfo(
        name="Tiger Analytics", category="Indian AI", prestige_score=7,
        ats_platform="custom",
        careers_url="https://www.tigeranalytics.com/careers/",
        estimated_salary_lpa=12,
    ),
    CompanyInfo(
        name="Tredence", category="Indian AI", prestige_score=6,
        ats_platform="custom",
        careers_url="https://www.tredence.com/careers",
        estimated_salary_lpa=12,
    ),
    CompanyInfo(
        name="Mu Sigma", category="Indian AI", prestige_score=6,
        ats_platform="custom",
        careers_url="https://www.mu-sigma.com/careers",
        estimated_salary_lpa=8,
    ),
    CompanyInfo(
        name="Mad Street Den", category="Indian AI", prestige_score=7,
        ats_platform="custom",
        careers_url="https://www.madstreetden.com/careers/",
        estimated_salary_lpa=12,
    ),
    CompanyInfo(
        name="Eightfold AI", category="AI Company", prestige_score=7,
        ats_platform="custom",
        careers_url="https://eightfold.ai/careers/",
        estimated_salary_lpa=20,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # INDIAN PRODUCT COMPANIES (Prestige 7-9)
    # ═══════════════════════════════════════════════════════════════════════════
    CompanyInfo(
        name="Flipkart", category="Indian Product", prestige_score=8,
        ats_platform="custom",
        careers_url="https://www.flipkartcareers.com/#!/joblist",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Walmart Labs", category="Indian Product", prestige_score=8,
        ats_platform="custom",
        careers_url="https://careers.walmart.com/results?q=machine+learning&page=1&sort=rank&expand=department,brand,type,rate&jobCareerArea=all",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Zoho", category="Indian Product", prestige_score=7,
        ats_platform="custom",
        careers_url="https://www.zoho.com/careers/jobs/",
        estimated_salary_lpa=12,
    ),
    CompanyInfo(
        name="Freshworks", category="Indian Product", prestige_score=8,
        ats_platform="custom",
        careers_url="https://www.freshworks.com/company/careers/jobs/",
        estimated_salary_lpa=18,
    ),
    CompanyInfo(
        name="Razorpay", category="Indian Product", prestige_score=8,
        ats_platform="custom",
        careers_url="https://razorpay.com/jobs/",
        estimated_salary_lpa=20,
    ),
    CompanyInfo(
        name="Zerodha", category="Indian Product", prestige_score=7,
        ats_platform="custom",
        careers_url="https://zerodha.com/careers/",
        estimated_salary_lpa=18,
    ),
    CompanyInfo(
        name="Groww", category="Indian Product", prestige_score=7,
        ats_platform="custom",
        careers_url="https://groww.in/careers",
        estimated_salary_lpa=18,
    ),
    CompanyInfo(
        name="Swiggy", category="Indian Product", prestige_score=7,
        ats_platform="custom",
        careers_url="https://careers.swiggy.com/",
        estimated_salary_lpa=18,
    ),
    CompanyInfo(
        name="Zomato", category="Indian Product", prestige_score=7,
        ats_platform="custom",
        careers_url="https://www.zomato.com/careers",
        estimated_salary_lpa=16,
    ),
    CompanyInfo(
        name="Juspay", category="Indian Product", prestige_score=7,
        ats_platform="custom",
        careers_url="https://juspay.in/careers",
        estimated_salary_lpa=16,
    ),
    CompanyInfo(
        name="Dream11", category="Indian Product", prestige_score=8,
        ats_platform="custom",
        careers_url="https://www.dreamsports.group/careers",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Paytm", category="Indian Product", prestige_score=7,
        ats_platform="custom",
        careers_url="https://paytm.com/careers",
        estimated_salary_lpa=15,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # HIGH-GROWTH STARTUPS (Prestige 7-9)
    # ═══════════════════════════════════════════════════════════════════════════
    CompanyInfo(
        name="Rippling", category="Startup", prestige_score=8,
        ats_platform="custom",
        careers_url="https://www.rippling.com/careers",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="BrowserStack", category="Startup", prestige_score=8,
        ats_platform="custom",
        careers_url="https://www.browserstack.com/careers",
        estimated_salary_lpa=22,
    ),
    CompanyInfo(
        name="Innovaccer", category="Startup", prestige_score=7,
        ats_platform="custom",
        careers_url="https://innovaccer.com/careers",
        estimated_salary_lpa=18,
    ),
    CompanyInfo(
        name="Glean", category="Startup", prestige_score=8,
        ats_platform="custom",
        careers_url="https://www.glean.com/careers",
        estimated_salary_lpa=25,
    ),
    CompanyInfo(
        name="Sprinklr", category="Product", prestige_score=7,
        ats_platform="custom",
        careers_url="https://www.sprinklr.com/careers/",
        estimated_salary_lpa=18,
    ),
    CompanyInfo(
        name="Hasura", category="Startup", prestige_score=7,
        ats_platform="custom",
        careers_url="https://hasura.io/careers",
        estimated_salary_lpa=18,
    ),
    CompanyInfo(
        name="Observe.AI", category="AI Company", prestige_score=7,
        ats_platform="custom",
        careers_url="https://www.observe.ai/company/careers",
        estimated_salary_lpa=18,
    ),
    CompanyInfo(
        name="Yellow.ai", category="AI Company", prestige_score=7,
        ats_platform="custom",
        careers_url="https://yellow.ai/careers/",
        estimated_salary_lpa=15,
    ),
]


def get_greenhouse_companies() -> list[CompanyInfo]:
    """Return companies using Greenhouse ATS."""
    return [c for c in COMPANIES if c.ats_platform == "greenhouse" and c.ats_board_token]


def get_lever_companies() -> list[CompanyInfo]:
    """Return companies using Lever ATS."""
    return [c for c in COMPANIES if c.ats_platform == "lever" and c.ats_board_token]


def get_prestige_score(company_name: str) -> int:
    """Look up prestige score for a company by name. Returns 5 as default."""
    name_lower = company_name.lower().strip()
    for company in COMPANIES:
        if company.name.lower() in name_lower or name_lower in company.name.lower():
            return company.prestige_score
    return 5  # default for unknown companies


def get_estimated_salary(company_name: str) -> int | None:
    """Look up estimated salary for a company by name."""
    name_lower = company_name.lower().strip()
    for company in COMPANIES:
        if company.name.lower() in name_lower or name_lower in company.name.lower():
            return company.estimated_salary_lpa
    return None


def get_company_category(company_name: str) -> str:
    """Look up category for a company by name."""
    name_lower = company_name.lower().strip()
    for company in COMPANIES:
        if company.name.lower() in name_lower or name_lower in company.name.lower():
            return company.category
    return "Other"
