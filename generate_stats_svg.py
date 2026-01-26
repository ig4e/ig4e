import os
import json
import datetime
from github import Github, Auth, GithubException
from cryptography.fernet import Fernet

# --- Configuration ---
CACHE_VERSION = "2.1.0"
GH_TOKEN = os.getenv('GH_TOKEN')
CACHE_KEY = os.getenv('CACHE_ENCRYPTION_KEY')
OUTPUT_DIR = "stats_output"
CACHE_FILE = os.path.join(OUTPUT_DIR, "stats_cache.enc")

# Colors
BG_COLOR = "#1f1f1f"
TEXT_COLOR = "#c9d1d9"
ACCENT_COLOR = "#58a6ff"
BORDER_COLOR = "#1f1f1f"

EXTENSION_MAP = {
    # Web Development
    '.js': 'JavaScript', '.jsx': 'JavaScript', '.mjs': 'JavaScript', '.cjs': 'JavaScript',
    '.ts': 'TypeScript', '.tsx': 'TypeScript', '.mts': 'TypeScript', '.cts': 'TypeScript',
    '.html': 'HTML', '.htm': 'HTML', '.xhtml': 'HTML',
    '.css': 'CSS', '.scss': 'SCSS', '.sass': 'Sass', '.less': 'Less',
    '.vue': 'Vue', '.svelte': 'Svelte', '.astro': 'Astro',

    # Systems Programming
    '.c': 'C', '.h': 'C', '.cats': 'C',
    '.cpp': 'C++', '.hpp': 'C++', '.cc': 'C++', '.hh': 'C++', '.cxx': 'C++', '.hxx': 'C++',
    '.rs': 'Rust', '.go': 'Go', '.zig': 'Zig', '.nim': 'Nim', '.v': 'Verilog',

    # General Purpose / Scripting
    '.py': 'Python', '.pyw': 'Python', '.pyi': 'Python',
    '.rb': 'Ruby', '.rbw': 'Ruby', '.rake': 'Ruby', '.gemspec': 'Ruby',
    '.php': 'PHP', '.phtml': 'PHP', '.php3': 'PHP', '.php4': 'PHP', '.php5': 'PHP',
    '.pl': 'Perl', '.pm': 'Perl', '.t': 'Perl',
    '.lua': 'Lua', '.dart': 'Dart', '.ex': 'Elixir', '.exs': 'Elixir',
    '.erl': 'Erlang', '.hrl': 'Erlang', '.swift': 'Swift',

    # JVM Languages
    '.java': 'Java', '.jsp': 'Java',
    '.kt': 'Kotlin', '.kts': 'Kotlin',
    '.scala': 'Scala', '.sc': 'Scala',
    '.groovy': 'Groovy', '.gvy': 'Groovy', '.gy': 'Groovy', '.gsh': 'Groovy',

    # .NET Languages
    '.cs': 'C#', '.fs': 'F#', '.fsx': 'F#', '.fsi': 'F#',
    '.vb': 'Visual Basic', '.vbs': 'VBScript',

    # Functional Programming
    '.hs': 'Haskell', '.lhs': 'Haskell',
    '.ml': 'OCaml', '.mli': 'OCaml',
    '.clj': 'Clojure', '.cljs': 'Clojure', '.cljc': 'Clojure', '.edn': 'Clojure',
    '.lsp': 'Lisp', '.lisp': 'Lisp', '.scm': 'Scheme', '.ss': 'Scheme',

    # Shell & DevOps
    '.sh': 'Shell', '.bash': 'Shell', '.zsh': 'Shell', '.ksh': 'Shell',
    '.ps1': 'PowerShell', '.psm1': 'PowerShell', '.psd1': 'PowerShell',
    '.bat': 'Batch', '.cmd': 'Batch',
    '.dockerfile': 'Docker', '.containerfile': 'Docker',
    '.tf': 'Terraform', '.tfvars': 'Terraform', '.hcl': 'HCL',
    '.yaml': 'YAML', '.yml': 'YAML',
    '.json': 'JSON', '.json5': 'JSON', '.jsonl': 'JSON',
    '.toml': 'TOML', '.ini': 'INI', '.cfg': 'Config', '.conf': 'Config',

    # Database
    '.sql': 'SQL', '.pgsql': 'SQL', '.mysql': 'SQL', '.cql': 'SQL',
    '.prisma': 'Prisma',

    # Documentation & Markup
    '.md': 'Markdown', '.markdown': 'Markdown', '.mdown': 'Markdown',
    '.rst': 'reStructuredText',
    '.tex': 'LaTeX', '.latex': 'LaTeX', '.bib': 'LaTeX',
    '.xml': 'XML', '.svg': 'SVG', '.rss': 'XML', '.xsd': 'XML', '.wsdl': 'XML',
    '.csv': 'CSV', '.tsv': 'CSV',

    # Game Development & Physics
    '.shader': 'ShaderLab', '.hlsl': 'HLSL', '.glsl': 'GLSL',
    '.vert': 'GLSL', '.frag': 'GLSL', '.geom': 'GLSL',
    '.gd': 'GDScript', '.unity': 'Unity',

    # Others
    '.asm': 'Assembly', '.s': 'Assembly', '.nasm': 'Assembly',
    '.r': 'R', '.rmd': 'R',
    '.jl': 'Julia',
    '.sol': 'Solidity',
    '.proto': 'Protocol Buffers',
    '.graphql': 'GraphQL', '.gql': 'GraphQL'
}

if not GH_TOKEN:
    raise Exception("GH_TOKEN is not set")

auth = Auth.Token(GH_TOKEN)
g = Github(auth=auth)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'rb') as f:
            data = f.read()
        
        if CACHE_KEY:
            try:
                f_obj = Fernet(CACHE_KEY.encode())
                data = f_obj.decrypt(data)
            except Exception as e:
                print(f"Warning: Decryption failed, starting with fresh cache. Error: {e}")
                return get_empty_cache()
        
        try:
            cache = json.loads(data.decode('utf-8'))
            if cache.get("version") != CACHE_VERSION:
                print(f"Notice: Cache version mismatch ({cache.get('version')} vs {CACHE_VERSION}). Starting fresh backfill.")
                return get_empty_cache()
            return cache
        except:
            return get_empty_cache()
    return get_empty_cache()

def get_empty_cache():
    return {
        "version": CACHE_VERSION,
        "daily_stats": {},
        "last_update": None,
        "processed_repos": {}
    }

def save_cache(cache):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = json.dumps(cache, indent=2).encode('utf-8')
    if CACHE_KEY:
        f_obj = Fernet(CACHE_KEY.encode())
        data = f_obj.encrypt(data)
    
    with open(CACHE_FILE, 'wb') as f:
        f.write(data)

def add_stat(cache, date_str, commits, additions, languages=None):
    if date_str not in cache["daily_stats"]:
        cache["daily_stats"][date_str] = {"commits": 0, "lines": 0, "languages": {}}
    
    cache["daily_stats"][date_str]["commits"] += commits
    cache["daily_stats"][date_str]["lines"] += additions
    
    if languages:
        daily_langs = cache["daily_stats"][date_str].setdefault("languages", {})
        for lang, count in languages.items():
            daily_langs[lang] = daily_langs.get(lang, 0) + count

def get_commit_languages(commit):
    langs = {}
    total_additions = 0
    try:
        for f in commit.files:
            _, ext = os.path.splitext(f.filename)
            lang = EXTENSION_MAP.get(ext.lower(), "Other")
            langs[lang] = langs.get(lang, 0) + f.additions
            total_additions += f.additions
    except:
        pass
    return langs, total_additions

def fetch_historical_stats(user, cache):
    print("Fetching historical stats from ALL accessible repositories... (This may take a while)")
    repos = list(user.get_repos(type='all'))
    total_repos = len(repos)
    
    for i, repo in enumerate(repos):
        if repo.full_name in cache["processed_repos"] and cache["processed_repos"][repo.full_name] == "COMPLETED":
            continue
        
        print(f"[{i+1}/{total_repos}] Processing: {repo.full_name}...")
        try:
            commits = list(repo.get_commits(author=user.login))
            if not commits:
                cache["processed_repos"][repo.full_name] = "COMPLETED"
                continue

            for j, commit in enumerate(commits):
                if j % 20 == 0:
                    print(f"  -> Fetching commit {j+1}/{len(commits)} in {repo.name}...")
                
                date_str = commit.commit.author.date.strftime("%Y-%m-%d")
                langs, additions = get_commit_languages(commit)
                add_stat(cache, date_str, 1, additions, languages=langs)
            
            cache["processed_repos"][repo.full_name] = "COMPLETED"
            save_cache(cache)
        except Exception as e:
            print(f"  Error processing {repo.full_name}: {e}")
            continue

def update_from_events(user, cache):
    print("\nUpdating stats from recent events...")
    last_update = cache.get("last_update")
    if last_update:
        last_update_dt = datetime.datetime.fromisoformat(last_update.replace("Z", "+00:00"))
    else:
        last_update_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)

    events = list(user.get_events())
    processed_count = 0
    
    for event in events:
        if event.created_at < last_update_dt:
            break
        
        if event.type == "PushEvent":
            commits_list = event.payload.get('commits', [])
            repo_name = event.repo.name
            date_str = event.created_at.strftime("%Y-%m-%d")
            
            print(f"  Processing push to {repo_name} on {date_str}...")
            try:
                repo = g.get_repo(repo_name)
                for commit_payload in commits_list:
                    # Get the full commit to get additions per language
                    commit = repo.get_commit(commit_payload['sha'])
                    # Verify the commit author is the user
                    if commit.author and commit.author.login == user.login:
                        langs, additions = get_commit_languages(commit)
                        add_stat(cache, date_str, 1, additions, languages=langs)
                processed_count += 1
            except Exception as e:
                print(f"  Skipped event: {e}")

    cache["last_update"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

def generate_svg(title, commits, lines, filename, languages=None):
    lang_svg = ""
    height = 120
    if languages:
        # Sort languages by lines
        sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        height = 140 + (len(sorted_langs) * 20)
        lang_svg = '<g transform="translate(25, 130)">'
        lang_svg += '<text x="0" y="0" class="stat">Top Languages (Lines)</text>'
        for i, (lang, count) in enumerate(sorted_langs):
            y_pos = 25 + (i * 20)
            lang_svg += f'<text x="5" y="{y_pos}" class="stat" style="font-weight:400">{lang}: {count:,}</text>'
        lang_svg += '</g>'

    svg_content = f"""
<svg width="400" height="{height}" viewBox="0 0 400 {height}" xmlns="http://www.w3.org/2000/svg">
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {ACCENT_COLOR}; }}
    .stat {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT_COLOR}; }}
    .number {{ font: 700 24px 'Segoe UI', Ubuntu, Sans-Serif; fill: #fff; }}
  </style>
  <rect x="0" y="0" width="400" height="{height}" rx="5" ry="5" fill="{BG_COLOR}" stroke="{BORDER_COLOR}" />
  
  <!-- Title -->
  <text x="25" y="35" class="header">{title}</text>
  
  <!-- Commits Stat -->
  <text x="25" y="80" class="stat">Commits Pushed</text>
  <text x="25" y="105" class="number">{commits:,}</text>
  
  <!-- Lines Stat -->
  <text x="200" y="80" class="stat">Lines Added</text>
  <text x="200" y="105" class="number">{lines:,}</text>
  
  {lang_svg}
</svg>
"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(svg_content)

def generate_stats_readme(OUTPUT_DIR, years):
    readme_content = f"""# 📊 Code Statistics Archive

This branch contains the generated statistics for @ig4e.

## 📅 Summary Stats
![Lifetime Stats](lifetime.svg)
![Yearly Stats](yearly.svg)
![Monthly Stats](monthly.svg)
![Weekly Stats](weekly.svg)

## 🗄️ Yearly Archive
"""
    for year in sorted(years.keys(), reverse=True):
        readme_content += f"- [{year} Statistics](years/{year}.svg)\n"
    
    readme_content += "\n---\n*Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    
    with open(os.path.join(OUTPUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

def main():
    user = g.get_user()
    cache = load_cache()

    # 1. Update data
    # If daily_stats is empty, we do a backfill once.
    if not cache["daily_stats"]:
        fetch_historical_stats(user, cache)
    
    update_from_events(user, cache)
    save_cache(cache)

    # 2. Process timeframes
    today = datetime.date.today()
    
    # Calculate different ranges
    ranges = {
        "weekly": 7,
        "monthly": 30,
        "yearly": 365,
    }
    
    # Yearly buckets
    years = {}
    
    total_commits = 0
    total_lines = 0
    total_langs = {}

    # Sort dates to process
    all_dates = sorted(cache["daily_stats"].keys())
    
    for date_str in all_dates:
        data = cache["daily_stats"][date_str]
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        year = dt.year
        
        # Totals
        total_commits += data["commits"]
        total_lines += data["lines"]
        for lang, count in data.get("languages", {}).items():
            total_langs[lang] = total_langs.get(lang, 0) + count
        
        # Yearly
        if year not in years:
            years[year] = {"commits": 0, "lines": 0, "languages": {}}
        years[year]["commits"] += data["commits"]
        years[year]["lines"] += data["lines"]
        for lang, count in data.get("languages", {}).items():
            years[year]["languages"][lang] = years[year]["languages"].get(lang, 0) + count

    # Generate Lifetime
    generate_svg("Lifetime Stats", total_commits, total_lines, os.path.join(OUTPUT_DIR, "lifetime.svg"), languages=total_langs)

    # Generate Last X Days
    for label, days in ranges.items():
        cutoff = today - datetime.timedelta(days=days)
        recent_commits = 0
        recent_lines = 0
        recent_langs = {}
        for date_str in all_dates:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            if dt >= cutoff:
                data = cache["daily_stats"][date_str]
                recent_commits += data["commits"]
                recent_lines += data["lines"]
                for lang, count in data.get("languages", {}).items():
                    recent_langs[lang] = recent_langs.get(lang, 0) + count
        
        generate_svg(f"{label.capitalize()} Stats", recent_commits, recent_lines, os.path.join(OUTPUT_DIR, f"{label}.svg"), languages=recent_langs)

    # Generate Year Archive
    for year, stats in years.items():
        generate_svg(f"Stats for {year}", stats["commits"], stats["lines"], os.path.join(OUTPUT_DIR, f"years/{year}.svg"), languages=stats["languages"])

    # Generate README for the stats branch
    generate_stats_readme(OUTPUT_DIR, years)

    print(f"Stats generation complete. Files saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()