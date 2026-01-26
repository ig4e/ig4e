package api

import (
	"context"
	"time"

	"github.com/google/go-github/v60/github"
	"github.com/shurcooL/githubv4"
	"golang.org/x/oauth2"
)

type Client struct {
	V4   *githubv4.Client
	REST *github.Client
}

func NewClient(token string) *Client {
	src := oauth2.StaticTokenSource(
		&oauth2.Token{AccessToken: token},
	)
	httpClient := oauth2.NewClient(context.Background(), src)
	return &Client{
		V4:   githubv4.NewClient(httpClient),
		REST: github.NewClient(httpClient),
	}
}

type ContributionQuery struct {
	Viewer struct {
		Login                   githubv4.String
		ContributionsCollection struct {
			TotalCommitContributions            githubv4.Int
			TotalPullRequestContributions       githubv4.Int
			TotalIssueContributions             githubv4.Int
			TotalPullRequestReviewContributions githubv4.Int
			RestrictedContributionsCount        githubv4.Int
			ContributionCalendar struct {
				Weeks []struct {
					ContributionDays []struct {
						ContributionCount githubv4.Int
						Date              githubv4.String
					}
				}
			}
			CommitContributionsByRepository     []struct {
				Repository struct {
					Name             githubv4.String
					Owner            struct{ Login githubv4.String }
					PrimaryLanguage struct {
						Name githubv4.String
						Color githubv4.String
					}
				}
				Contributions struct {
					TotalCount githubv4.Int
				}
			}
		} `graphql:"contributionsCollection(from: $from, to: $to)"`
	}
}

func (c *Client) FetchContributions(ctx context.Context, from, to time.Time) (*ContributionQuery, error) {
	var q ContributionQuery
	variables := map[string]interface{}{
		"from": githubv4.DateTime{Time: from},
		"to":   githubv4.DateTime{Time: to},
	}
	err := c.V4.Query(ctx, &q, variables)
	return &q, err
}

type RepoQuery struct {
	Viewer struct {
		Repositories struct {
			Nodes []struct {
				Name             githubv4.String
				StargazerCount   githubv4.Int
				ForkCount        githubv4.Int
				PrimaryLanguage struct {
					Name githubv4.String
					Color githubv4.String
				}
				Languages struct {
					Edges []struct {
						Size githubv4.Int
						Node struct {
							Name  githubv4.String
							Color githubv4.String
						}
					}
				} `graphql:"languages(first: 10, orderBy: {field: SIZE, direction: DESC})"`
			}
		} `graphql:"repositories(first: 100, ownerAffiliations: OWNER, isFork: false)"`
	}
}

func (c *Client) FetchRepos(ctx context.Context) (*RepoQuery, error) {
	var q RepoQuery
	err := c.V4.Query(ctx, &q, nil)
	return &q, err
}
