import glob, re
for f in glob.glob('d:/Final Projects/JOB_ALERT/scrapers/*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    if 'config.companies' in content:
        content = re.sub(r'from config\.companies import.*\n', '', content)
        content = re.sub(r'company_prestige_score=get_prestige_score\([^)]+\),', 'company_prestige_score=company.get("priority", False) and 10 or 5,', content)
        content = re.sub(r'estimated_salary_lpa=get_estimated_salary\([^)]+\),', 'estimated_salary_lpa=None,', content)
        content = re.sub(r'company_category=get_company_category\([^)]+\)', 'company_category=company.get("category")', content)
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
