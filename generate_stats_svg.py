import os
import datetime
from github import Github, Auth

# --- Configuration ---
GH_TOKEN = os.getenv('GH_TOKEN')
DAYS = 7
# Colors to match your existing theme (Dark mode)
BG_COLOR = "#1f1f1f"
TEXT_COLOR = "#c9d1d9"
ACCENT_COLOR = "#58a6ff" # GitHub Blue
BORDER_COLOR = "#1f1f1f" 

if not GH_TOKEN:
    raise Exception("GH_TOKEN is not set")

# Fix: Use Auth.Token to avoid DeprecationWarning
auth = Auth.Token(GH_TOKEN)
g = Github(auth=auth)

# --- Fetch Data ---
# Fix: Use timezone.utc to make the date "offset-aware"
start_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DAYS)
total_lines = 0
total_commits = 0

user = g.get_user()
print(f"Fetching stats for {user.login} since {start_date.date()}...")

# Iterate through events (PushEvent)
for event in user.get_events():
    # Fix: Ensure event date is compared correctly
    if event.created_at < start_date:
        break
    
    if event.type == "PushEvent":
        commits = event.payload.get('commits', [])
        total_commits += event.payload.get('size', len(commits))
        repo_name = event.repo.name
        
        try:
            repo = g.get_repo(repo_name)
            for commit_payload in commits:
                # Fetch full commit details to get line additions
                c = repo.get_commit(commit_payload['sha'])
                total_lines += c.stats.additions
                print(f" + {c.stats.additions} lines in {repo_name}")
        except Exception as e:
            print(f"  Skipped repo {repo_name}: {e}")

# --- Generate SVG ---
svg_content = f"""
<svg width="400" height="120" viewBox="0 0 400 120" xmlns="http://www.w3.org/2000/svg">
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {ACCENT_COLOR}; }}
    .stat {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT_COLOR}; }}
    .number {{ font: 700 24px 'Segoe UI', Ubuntu, Sans-Serif; fill: #fff; }}
  </style>
  <rect x="0" y="0" width="400" height="120" rx="5" ry="5" fill="{BG_COLOR}" stroke="{BORDER_COLOR}" />
  
  <!-- Title -->
  <text x="25" y="35" class="header">Weekly Code Output</text>
  
  <!-- Commits Stat -->
  <text x="25" y="80" class="stat">Commits Pushed</text>
  <text x="25" y="105" class="number">{total_commits}</text>
  
  <!-- Lines Stat -->
  <text x="200" y="80" class="stat">Lines Added</text>
  <text x="200" y="105" class="number">{total_lines:,}</text>
</svg>
"""

# --- Save file ---
with open("weekly_stats.svg", "w", encoding="utf-8") as f:
    f.write(svg_content)

print(f"Generated SVG: {total_commits} commits, {total_lines} lines.")