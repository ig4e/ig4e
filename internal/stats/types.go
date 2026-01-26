package stats

import "time"

type LanguageStat struct {
	Name  string  `json:"name"`
	Size  int64   `json:"size"`
	Color string  `json:"color"`
}

type DailyStats struct {
	Date         time.Time            `json:"date"`
	Commits      int                  `json:"commits"`
	PRs          int                  `json:"prs"`
	Issues       int                  `json:"issues"`
	Reviews      int                  `json:"reviews"`
	Additions    int                  `json:"additions"`
	Deletions    int                  `json:"deletions"`
	LangLines    map[string]int       `json:"lang_lines"` // Lines added per language
	RepoByteSize map[string]int64     `json:"repo_bytes"` // Total bytes per language (composition)
}

type Cache struct {
	Version        string                `json:"version"`
	LastUpdate     time.Time             `json:"last_update"`
	DailyStats     map[string]DailyStats `json:"daily_stats"`
	ProcessedRepos map[string]bool      `json:"processed_repos"`
	TotalStars     int                   `json:"total_stars"`
}

func NewCache() *Cache {
	return &Cache{
		Version:        "3.0.0",
		DailyStats:     make(map[string]DailyStats),
		ProcessedRepos: make(map[string]bool),
	}
}
