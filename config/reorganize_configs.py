import os, json, glob

src_dir = r"d:\Final Projects\JOB_ALERT\config\companies"
out_files = {
    "official": [], "greenhouse": [], "lever": [], "ashby": [], "workday": [], 
    "workable": [], "smartrecruiters": [], "teamtailor": [], "jobvite": [], 
    "recruitee": [], "bamboohr": [], "personio": [], "comeet": [], "icims": [], 
    "oracle": [], "sap": [], "github_sources": [], "priority_companies": []
}

all_companies = {}

# 1. Read all companies
for file in glob.glob(os.path.join(src_dir, "*.json")):
    with open(file, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                for c in data:
                    all_companies[c['name']] = c
        except Exception:
            pass
            
# 2. Sort into buckets
for name, c in all_companies.items():
    ats = c.get('ats', 'official').lower()
    
    # Optional formatting to meet V2 spec
    if 'career_url' not in c and 'ats_url' in c:
        c['career_url'] = c['ats_url']
        
    if ats in out_files:
        out_files[ats].append(c)
    else:
        out_files['official'].append(c)

# 3. Write back and delete old unmapped
for file in glob.glob(os.path.join(src_dir, "*.json")):
    try:
        os.remove(file)
    except:
        pass

for ats, companies in out_files.items():
    with open(os.path.join(src_dir, f"{ats}.json"), 'w', encoding='utf-8') as f:
        json.dump(companies, f, indent=4)
        
print("Reorganized config files successfully!")
