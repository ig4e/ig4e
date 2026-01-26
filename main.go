package main

import (
	"context"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/google/go-github/v60/github"
	"github.com/go-enry/go-enry/v2"
	"github.com/ig4e/ig4e/internal/api"
	"github.com/ig4e/ig4e/internal/crypto"
	"github.com/ig4e/ig4e/internal/stats"
	"github.com/ig4e/ig4e/internal/templates"
)

const (
	OutputDir = "stats_output"
	CacheFile = "stats_cache.enc"
)

func main() {
	token := os.Getenv("GH_TOKEN")
	cacheKey := os.Getenv("CACHE_ENCRYPTION_KEY")
	if token == "" {
		log.Fatal("GH_TOKEN is missing")
	}

	client := api.NewClient(token)
	ctx := context.Background()

	// 1. Load Cache
	cache := loadCache(cacheKey)

	// 2. Fetch Data
	now := time.Now()
	
	// If empty, backfill 1 year
	if len(cache.DailyStats) == 0 {
		fmt.Println("Empty cache, performing initial backfill...")
		backfill(ctx, client, cache, now.AddDate(-1, 0, 0), now)
	} else {
		// Update from last update or last 7 days to be safe
		start := cache.LastUpdate.AddDate(0, 0, -2)
		if start.IsZero() {
			start = now.AddDate(0, 0, -30)
		}
		fmt.Printf("Updating stats since %s...\n", start.Format("2006-01-02"))
		fetchRange(ctx, client, cache, start, now)
	}

	cache.LastUpdate = now
	saveCache(cache, cacheKey)

	// 3. Generate SVGs
	generateAllSVGs(cache)
}

func loadCache(key string) *stats.Cache {
	path := filepath.Join(OutputDir, CacheFile)
	data, err := os.ReadFile(path)
	if err != nil {
		return stats.NewCache()
	}

	if key != "" {
		decrypted, err := crypto.Decrypt(data, []byte(padKey(key)))
		if err == nil {
			data = decrypted
		} else {
			fmt.Printf("Warning: Cache decryption failed: %v. Starting fresh.\n", err)
			return stats.NewCache()
		}
	}

	var cache stats.Cache
	if err := json.Unmarshal(data, &cache); err != nil {
		return stats.NewCache()
	}
	return &cache
}

func saveCache(cache *stats.Cache, key string) {
	os.MkdirAll(OutputDir, 0755)
	data, _ := json.MarshalIndent(cache, "", "  ")

	if key != "" {
		encrypted, err := crypto.Encrypt(data, []byte(padKey(key)))
		if err == nil {
			data = encrypted
		}
	}

	os.WriteFile(filepath.Join(OutputDir, CacheFile), data, 0644)
}

func padKey(key string) string {
	if len(key) >= 32 {
		return key[:32]
	}
	return key + strings.Repeat("0", 32-len(key))
}

func fetchRange(ctx context.Context, client *api.Client, cache *stats.Cache, from, to time.Time) {
	resp, err := client.FetchContributions(ctx, from, to)
	if err != nil {
		log.Printf("Error fetching contributions: %v", err)
		return
	}

	// 1. Map Calendar (Daily Commits)
	for _, week := range resp.Viewer.ContributionsCollection.ContributionCalendar.Weeks {
		for _, day := range week.ContributionDays {
			dateStr := string(day.Date)
			count := int(day.ContributionCount)
			if count > 0 {
				s := cache.DailyStats[dateStr]
				s.Commits = count
				cache.DailyStats[dateStr] = s
			}
		}
	}

	// 2. Add PRs, Issues, Reviews
	latestKey := to.Format("2006-01-02")
	s := cache.DailyStats[latestKey]
	s.PRs = int(resp.Viewer.ContributionsCollection.TotalPullRequestContributions)
	s.Issues = int(resp.Viewer.ContributionsCollection.TotalIssueContributions)
	s.Reviews = int(resp.Viewer.ContributionsCollection.TotalPullRequestReviewContributions)

	// 2.5 Fetch Detailed Commit Stats (Additions/Deletions per Language)
	fetchCommitDetails(ctx, client, cache, from, to)

	// 3. Language distribution and Stars from repos
	repos, _ := client.FetchRepos(ctx)
	if repos != nil {
		langMap := make(map[string]int64)
		totalStars := 0
		for _, node := range repos.Viewer.Repositories.Nodes {
			totalStars += int(node.StargazerCount)
			for _, edge := range node.Languages.Edges {
				langMap[string(edge.Node.Name)] += int64(edge.Size)
			}
		}
		s.RepoByteSize = langMap
		cache.TotalStars = totalStars
	}
	cache.DailyStats[latestKey] = s
}

func fetchCommitDetails(ctx context.Context, client *api.Client, cache *stats.Cache, from, to time.Time) {
	fmt.Println("Fetching detailed commit activity in parallel...")
	user, _, err := client.REST.Users.Get(ctx, "")
	if err != nil || user == nil || user.Login == nil {
		fmt.Printf("Error: Could not retrieve user profile: %v\n", err)
		return
	}

	repos, _, err := client.REST.Repositories.List(ctx, "", &github.RepositoryListOptions{Type: "owner"})
	if err != nil {
		fmt.Printf("Error: Could not list repositories: %v\n", err)
		return
	}

	var wg sync.WaitGroup
	var mu sync.Mutex
	semaphore := make(chan struct{}, 5) // Limit concurrency to avoid secondary rate limits

	for _, repo := range repos {
		if repo.Name == nil || repo.Owner == nil || repo.Owner.Login == nil {
			continue
		}

		wg.Add(1)
		go func(r *github.Repository) {
			defer wg.Done()
			semaphore <- struct{}{}        // Acquire
			defer func() { <-semaphore }() // Release

			commits, _, err := client.REST.Repositories.ListCommits(ctx, *r.Owner.Login, *r.Name, &github.CommitsListOptions{
				Author: *user.Login,
				Since:  from,
				Until:  to,
			})
			if err != nil {
				return
			}

			for _, commit := range commits {
				if commit.SHA == nil {
					continue
				}
				fullCommit, _, err := client.REST.Repositories.GetCommit(ctx, *r.Owner.Login, *r.Name, *commit.SHA, nil)
				if err != nil || fullCommit == nil {
					continue
				}

				dateStr := fullCommit.Commit.Author.Date.Format("2006-01-02")
				
				mu.Lock()
				daily := cache.DailyStats[dateStr]
				if daily.LangLines == nil {
					daily.LangLines = make(map[string]int)
				}

				for _, file := range fullCommit.Files {
					if file.Filename == nil || file.Additions == nil {
						continue
					}
					ext := filepath.Ext(*file.Filename)
					lang, _ := enry.GetLanguageByExtension(ext)
					if lang == "" {
						lang = "Other"
					}
					daily.LangLines[lang] += *file.Additions
					daily.Additions += *file.Additions
					daily.Deletions += *file.Deletions
				}
				cache.DailyStats[dateStr] = daily
				mu.Unlock()
			}
		}(repo)
	}

	wg.Wait()
	fmt.Println("Parallel commit processing complete.")
}

func backfill(ctx context.Context, client *api.Client, cache *stats.Cache, from, to time.Time) {
	// One year backfill
	fetchRange(ctx, client, cache, from, to)
}

func generateAllSVGs(cache *stats.Cache) {
	now := time.Now()

	// 1. Lifetime
	genSummary(cache, "Lifetime Stats", time.Time{}, "lifetime.svg")

	// 2. Yearly (Last 365 days)
	genSummary(cache, "Yearly Stats", now.AddDate(-1, 0, 0), "yearly.svg")

	// 3. Monthly (Last 30 days)
	genSummary(cache, "Monthly Stats", now.AddDate(0, -1, 0), "monthly.svg")

	// 4. Weekly (Last 7 days)
	genSummary(cache, "Weekly Stats", now.AddDate(0, 0, -7), "weekly.svg")
}

func genSummary(cache *stats.Cache, title string, since time.Time, filename string) {
	var commits, prs, issues, reviews, totalAdditions int
	langs := make(map[string]int64)

	for dateStr, s := range cache.DailyStats {
		dt, _ := time.Parse("2006-01-02", dateStr)
		if !since.IsZero() && dt.Before(since) {
			continue
		}
		commits += s.Commits
		prs += s.PRs
		issues += s.Issues
		reviews += s.Reviews
		totalAdditions += s.Additions

		// Use LangLines (activity) for summary if available, else RepoByteSize (composition)
		for l, lines := range s.LangLines {
			langs[l] += int64(lines)
		}
		if len(s.LangLines) == 0 {
			for l, size := range s.RepoByteSize {
				langs[l] += size
			}
		}
	}

	renderSVG(title, commits, prs, issues, reviews, totalAdditions, cache.TotalStars, langs, filename)
}

func renderSVG(title string, commits, prs, issues, reviews, lines, stars int, langs map[string]int64, filename string) {
	funcMap := template.FuncMap{
		"mul": templates.Mul,
		"add": templates.Add,
	}
	tmpl, err := template.New("stats").Funcs(funcMap).Parse(templates.StatsTemplate)
	if err != nil {
		log.Fatal(err)
	}

	// Sort and process languages
	type langItem struct {
		name  string
		size  int64
		color string
	}
	var sortedLangs []langItem
	var totalSize int64
	for name, size := range langs {
		color := enry.GetColor(name)
		if color == "" {
			color = "#ccc"
		}
		sortedLangs = append(sortedLangs, langItem{name: name, size: size, color: color})
		totalSize += size
	}
	sort.Slice(sortedLangs, func(i, j int) bool { return sortedLangs[i].size > sortedLangs[j].size })

	if len(sortedLangs) > 5 {
		sortedLangs = sortedLangs[:5]
	}

	var svgLangs []templates.SVGLang
	offset := 0.0
	for _, l := range sortedLangs {
		width := (float64(l.size) / float64(totalSize)) * 380
		svgLangs = append(svgLangs, templates.SVGLang{
			Name:   l.name,
			Size:   l.size,
			Color:  l.color,
			Width:  width,
			Offset: offset,
		})
		offset += width
	}

	data := templates.SVGData{
		Title:       title,
		Commits:     fmt.Sprintf("%d", commits),
		PRs:         fmt.Sprintf("%d", prs),
		Issues:      fmt.Sprintf("%d", issues),
		Reviews:     fmt.Sprintf("%d", reviews),
		Lines:       fmt.Sprintf("%d", lines),
		Stars:       fmt.Sprintf("%d", stars),
		Languages:   svgLangs,
		AccentColor: "#58a6ff",
		TextColor:   "#c9d1d9",
		BgColor:     "#0d1117",
		BorderColor: "#30363d",
	}

	f, err := os.Create(filepath.Join(OutputDir, filename))
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()

	tmpl.Execute(f, data)
}
