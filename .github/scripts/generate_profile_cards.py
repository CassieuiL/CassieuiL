"""Generate profile cards from public REST data. No personal token is required."""
import json
import os
import re
import textwrap
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path

OWNER = os.environ.get('PROFILE_OWNER', 'CassieuiL')
if not re.fullmatch(r'[A-Za-z0-9-]+', OWNER):
    raise ValueError('Invalid GitHub username')
OUT = Path('dist')
OUT.mkdir(exist_ok=True)
HEADERS = {'Accept': 'application/vnd.github+json', 'User-Agent': 'CassieuiL-profile-cards', 'X-GitHub-Api-Version': '2022-11-28'}

def get(path):
    request = urllib.request.Request('https://api.github.com' + path, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

profile = get(f'/users/{OWNER}')
repos = []
for page in range(1, 101):
    batch = get(f'/users/{OWNER}/repos?type=owner&per_page=100&page={page}')
    if not isinstance(batch, list):
        raise ValueError('Repository response must be a list')
    repos.extend(r for r in batch if not r.get('private', True))
    if len(batch) < 100:
        break
else:
    raise ValueError('Repository pagination limit exceeded')

original = [r for r in repos if not r['fork']]
code_repos = [r for r in original if r['name'].lower() != OWNER.lower()]
languages = Counter()
for repo in code_repos:
    for language, size in get(f"/repos/{OWNER}/{repo['name']}/languages").items():
        languages[language] += size

def text(x, y, value, size=14, color='#c9d1d9', weight='400'):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}">{escape(str(value))}</text>'

def card(width, height, title, contents):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title, quote=True)}">
<title>{escape(title)}</title>
<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="8" fill="#0d1117" stroke="#30363d"/>
<g font-family="Segoe UI,Ubuntu,Arial,sans-serif">{text(24,34,title,18,'#58d5e5','600')}{contents}</g></svg>'''

stats = [('Public repositories', len(repos)), ('Stars received', sum(r['stargazers_count'] for r in original)), ('Forks received', sum(r['forks_count'] for r in original)), ('Followers', profile['followers'])]
rows = ''.join(text(25, 70+i*27, label, 14) + text(370,70+i*27,value,14,'#e6edf3','600') for i,(label,value) in enumerate(stats))
(OUT/'stats.svg').write_text(card(430,190,'Public GitHub Stats',rows),encoding='utf-8')

colors={'Python':'#3572a5','C++':'#f34b7d','Shell':'#89e051','C':'#555555','CMake':'#da3434','JavaScript':'#f1e05a','HTML':'#e34c26','CSS':'#563d7c','Jupyter Notebook':'#da5b0b'}
ordered=languages.most_common()
shown=ordered[:5]
if len(ordered)>5:
    shown.append(('Other',sum(v for _,v in ordered[5:])))
total=sum(languages.values())
if total <= 0:
    raise ValueError('No language data returned')
x=24.0
body=''
for name,size in shown:
    width=312*size/total
    body+=f'<rect x="{x:.3f}" y="57" width="{width:.3f}" height="9" fill="{colors.get(name,"#8b949e")}"/>'
    x+=width
for i,(name,size) in enumerate(shown):
    col,row=i%2,i//2
    x=24+col*163; y=94+row*26
    body+=f'<circle cx="{x+4}" cy="{y-4}" r="4" fill="{colors.get(name,"#8b949e")}"/>'
    body+=text(x+15,y,f'{name} {100*size/total:.1f}%',12)
body+=text(24,170,'Original code repositories · by bytes',10,'#8b949e')
(OUT/'languages.svg').write_text(card(360,190,'Code Languages',body),encoding='utf-8')

selected=[('cv-research-videomae','videomae','VideoMAE on UCF101: temporal ablations and pretraining transfer.'),('robocup-home-service-sim','planner','World-state reasoning and constraint-aware planning for service robots in simulation.')]
by_name={r['name']:r for r in repos}
for name,filename,description in selected:
    repo=by_name[name]
    body=''
    for i,line in enumerate(textwrap.wrap(description,width=48)):
        body+=text(24,65+i*20,line,13,'#9da7b3')
    language=repo.get('language') or 'Code'
    body+=f'<circle cx="29" cy="130" r="5" fill="{colors.get(language,"#8b949e")}"/>'
    body+=text(42,135,language,12)
    body+=text(172,135,f"Stars {repo['stargazers_count']}",12,'#8b949e')
    body+=text(270,135,f"Forks {repo['forks_count']}",12,'#8b949e')
    (OUT/f'{filename}.svg').write_text(card(420,158,name,body),encoding='utf-8')

snapshot={'generated_at':datetime.now(timezone.utc).isoformat(),'scope':'Public repositories only; stars/forks exclude forks; languages exclude forks and profile repository.','stats':dict(stats),'language_bytes':dict(languages)}
(OUT/'data.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
print(f'Generated four SVG cards from {len(repos)} public repositories.')
