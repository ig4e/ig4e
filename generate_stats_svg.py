import os
import json
import datetime
from github import Github, Auth, GithubException
from cryptography.fernet import Fernet

# --- Configuration ---
GH_TOKEN = os.getenv('GH_TOKEN')
CACHE_KEY = os.getenv('CACHE_ENCRYPTION_KEY')
OUTPUT_DIR = "stats_output"
CACHE_FILE = os.path.join(OUTPUT_DIR, "stats_cache.enc")

# Colors to match theme
BG_COLOR = "#1f1f1f"
TEXT_COLOR = "#c9d1d9"
ACCENT_COLOR = "#58a6ff"  # GitHub Blue
BORDER_COLOR = "#1f1f1f"

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
        
        return json.loads(data.decode('utf-8'))
    return get_empty_cache()

def get_empty_cache():
    return {
        "daily_stats": {},
        "last_update": None,
        "processed_repos": {} # repo_full_name: last_commit_sha_processed
    }

def save_cache(cache):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = json.dumps(cache, indent=2).encode('utf-8')
    if CACHE_KEY:
        f_obj = Fernet(CACHE_KEY.encode())
        data = f_obj.encrypt(data)
    
    with open(CACHE_FILE, 'wb') as f:
        f.write(data)

def add_stat(cache, date_str, commits, lines):
    if date_str not in cache["daily_stats"]:
        cache["daily_stats"][date_str] = {"commits": 0, "lines": 0}
    cache["daily_stats"][date_str]["commits"] += commits
    cache["daily_stats"][date_str]["lines"] += lines

def fetch_historical_stats(user, cache):
    """
    Fallback method to get stats from all repos if cache is empty or for initial setup.
    This can be very slow and hit rate limits, so we cache repo progress.
    """
    print("Fetching historical stats from repositories... (This may take a while)")
    repos = list(user.get_repos(type='owner'))
    total_repos = len(repos)
    
    for i, repo in enumerate(repos):
        if repo.fork: 
            print(f"[{i+1}/{total_repos}] Skipping fork: {repo.full_name}")
            continue
            
        if repo.full_name in cache["processed_repos"] and cache["processed_repos"][repo.full_name] == "COMPLETED":
            print(f"[{i+1}/{total_repos}] Already processed: {repo.full_name}")
            continue
        
        print(f"[{i+1}/{total_repos}] Processing: {repo.full_name}...")
        try:
            commits = list(repo.get_commits(author=user.login))
            num_commits = len(commits)
            for j, commit in enumerate(commits):
                if j % 10 == 0: # Log every 10 commits to avoid flooding
                    print(f"  -> Fetching commit {j+1}/{num_commits} in {repo.name}...")
                
                date_str = commit.commit.author.date.strftime("%Y-%m-%d")
                add_stat(cache, date_str, 1, commit.stats.additions)
            
            cache["processed_repos"][repo.full_name] = "COMPLETED"
            save_cache(cache)
            print(f"  ✓ Finished {repo.full_name}")
        except GithubException as e:
            print(f"  Error processing {repo.full_name}: {e}")
            continue

def update_from_events(user, cache):
    """
    Incremental update using the Events API (last 90 days / 300 events).
    """
    print("\nUpdating stats from recent events...")
    last_update = cache.get("last_update")
    if last_update:
        last_update_dt = datetime.datetime.fromisoformat(last_update.replace("Z", "+00:00"))
    else:
        last_update_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)

    events = list(user.get_events())
    print(f"Checking {len(events)} recent events...")
    
    processed_count = 0
    for event in events:
        if event.created_at < last_update_dt:
            break
        
        if event.type == "PushEvent":
            commits_list = event.payload.get('commits', [])
            num_commits = event.payload.get('size', len(commits_list))
            repo_name = event.repo.name
            date_str = event.created_at.strftime("%Y-%m-%d")
            
            print(f"  Processing push to {repo_name} on {date_str} ({num_commits} commits)...")
            try:
                repo = g.get_repo(repo_name)
                total_lines = 0
                for i, commit_payload in enumerate(commits_list):
                    c = repo.get_commit(commit_payload['sha'])
                    total_lines += c.stats.additions
                
                add_stat(cache, date_str, num_commits, total_lines)
                processed_count += 1
            except Exception as e:
                print(f"  Skipped repo {repo_name} event: {e}")

    print(f"Done. Processed {processed_count} new push events.")
    cache["last_update"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

def generate_svg(title, commits, lines, filename):
    svg_content = f"""
<svg width="400" height="120" viewBox="0 0 400 120" xmlns="http://www.w3.org/2000/svg">
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {ACCENT_COLOR}; }}
    .stat {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT_COLOR}; }}
    .number {{ font: 700 24px 'Segoe UI', Ubuntu, Sans-Serif; fill: #fff; }}
  </style>
  <rect x="0" y="0" width="400" height="120" rx="5" ry="5" fill="{BG_COLOR}" stroke="{BORDER_COLOR}" />
  
  <!-- Title -->
  <text x="25" y="35" class="header">{title}</text>
  
  <!-- Commits Stat -->
  <text x="25" y="80" class="stat">Commits Pushed</text>
  <text x="25" y="105" class="number">{commits:,}</text>
  
  <!-- Lines Stat -->
  <text x="200" y="80" class="stat">Lines Added</text>
  <text x="200" y="105" class="number">{lines:,}</text>
</svg>
"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(svg_content)

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

    # Sort dates to process
    all_dates = sorted(cache["daily_stats"].keys())
    
    for date_str in all_dates:
        data = cache["daily_stats"][date_str]
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        year = dt.year
        
        # Totals
        total_commits += data["commits"]
        total_lines += data["lines"]
        
        # Yearly
        if year not in years:
            years[year] = {"commits": 0, "lines": 0}
        years[year]["commits"] += data["commits"]
        years[year]["lines"] += data["lines"]

    # Generate Lifetime
    generate_svg("Lifetime Stats", total_commits, total_lines, os.path.join(OUTPUT_DIR, "lifetime.svg"))

    # Generate Last X Days
    for label, days in ranges.items():
        cutoff = today - datetime.timedelta(days=days)
        recent_commits = 0
        recent_lines = 0
        for date_str in all_dates:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            if dt >= cutoff:
                recent_commits += cache["daily_stats"][date_str]["commits"]
                recent_lines += cache["daily_stats"][date_str]["lines"]
        
        generate_svg(f"{label.capitalize()} Stats", recent_commits, recent_lines, os.path.join(OUTPUT_DIR, f"{label}.svg"))

    # Generate Year Archive
    for year, stats in years.items():
        generate_svg(f"Stats for {year}", stats["commits"], stats["lines"], os.path.join(OUTPUT_DIR, f"years/{year}.svg"))

    print(f"Stats generation complete. Files saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()