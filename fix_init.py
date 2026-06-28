import glob, re
for f in glob.glob('d:/Final Projects/JOB_ALERT/scrapers/*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # replace super().__init__("name") with super().__init__("name", session, semaphore)
    content = re.sub(r'super\(\)\.__init__\(([\"\'a-zA-Z0-9_]+)\)', r'super().__init__(\1, session, semaphore)', content)
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
