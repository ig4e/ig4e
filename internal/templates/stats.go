package templates

const StatsTemplate = `
<svg width="450" height="300" viewBox="0 0 450 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .header { font: 700 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {{.AccentColor}}; }
    .stat-label { font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: {{.TextColor}}; opacity: 0.8; }
    .stat-value { font: 700 22px 'Segoe UI', Ubuntu, Sans-Serif; fill: #fff; }
    .lang-label { font: 400 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: {{.TextColor}}; }
    .bento { fill: {{.BgColor}}; stroke: {{.BorderColor}}; stroke-width: 1; }
  </style>
  
  <rect width="450" height="300" rx="12" fill="{{.BgColor}}" />
  <rect x="15" y="15" width="420" height="270" rx="8" class="bento" />

  <!-- Header -->
  <text x="35" y="50" class="header">{{.Title}}</text>

  <!-- Grid -->
  <g transform="translate(35, 75)">
    <!-- Row 1 -->
    <text x="0" y="0" class="stat-label">Commits</text>
    <text x="0" y="25" class="stat-value">{{.Commits}}</text>
    
    <text x="200" y="0" class="stat-label">Pull Requests</text>
    <text x="200" y="25" class="stat-value">{{.PRs}}</text>
    
    <!-- Row 2 -->
    <text x="0" y="60" class="stat-label">Issues / Reviews</text>
    <text x="0" y="85" class="stat-value">{{.Issues}} / {{.Reviews}}</text>
    
    <text x="200" y="60" class="stat-label">Lines Added</text>
    <text x="200" y="85" class="stat-value">{{.Lines}}</text>

    <!-- Stars -->
    <text x="210" y="115" class="stat-label" style="text-anchor: middle;">Total Stars: {{.Stars}}</text>
  </g>

  <!-- Language Progress Bar -->
  <g transform="translate(35, 200)">
    <text x="0" y="0" class="stat-label">Top Languages</text>
    <rect x="0" y="15" width="380" height="8" rx="4" fill="#333" />
    <g transform="translate(0, 15)">
      {{range $i, $lang := .Languages}}
        <rect x="{{$lang.Offset}}" y="0" width="{{$lang.Width}}" height="8" fill="{{$lang.Color}}" {{if eq $i 0}}rx="4"{{end}} />
      {{end}}
    </g>
    
    <!-- Lang Legend -->
    <g transform="translate(0, 40)">
      {{range $i, $lang := .Languages}}
        {{if lt $i 5}}
        <circle cx="{{mul $i 80}}" cy="0" r="4" fill="{{$lang.Color}}" />
        <text x="{{add (mul $i 80) 10}}" y="4" class="lang-label">{{$lang.Name}}</text>
        {{end}}
      {{end}}
    </g>
  </g>
</svg>
`

type SVGData struct {
	Title       string
	Commits     string
	PRs         string
	Issues      string
	Reviews     string
	Lines       string
	Stars       string
	Languages   []SVGLang
	AccentColor string
	TextColor   string
	BgColor     string
	BorderColor string
}

type SVGLang struct {
	Name   string
	Size   int64
	Color  string
	Width  float64
	Offset float64
}

// Add useful template functions
func Mul(a, b int) int { return a * b }
func Add(a, b int) int { return a + b }
