package templates

const StatsTemplate = `
<svg width="450" height="340" viewBox="0 0 450 340" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .header { font: 700 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {{.AccentColor}}; }
    .stat-label { font: 600 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: {{.TextColor}}; opacity: 0.7; }
    .stat-value { font: 700 20px 'Segoe UI', Ubuntu, Sans-Serif; fill: #fff; }
    .lang-label { font: 400 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: {{.TextColor}}; }
    .lang-value { font: 700 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #fff; opacity: 0.9; }
    .bento { fill: {{.BgColor}}; stroke: {{.BorderColor}}; stroke-width: 1; }
  </style>
  
  <rect width="450" height="340" rx="12" fill="{{.BgColor}}" />
  <rect x="15" y="15" width="420" height="310" rx="8" class="bento" />

  <!-- Header -->
  <text x="35" y="50" class="header">{{.Title}}</text>

  <!-- Grid Analytics -->
  <g transform="translate(35, 75)">
    <!-- Column 1 -->
    <text x="0" y="0" class="stat-label">Commits</text>
    <text x="0" y="22" class="stat-value">{{.Commits}}</text>
    
    <text x="0" y="55" class="stat-label">Lines Added</text>
    <text x="0" y="77" class="stat-value">{{.Lines}}</text>
    
    <text x="0" y="110" class="stat-label">Active Days</text>
    <text x="0" y="132" class="stat-value">{{.ActiveDays}}</text>

    <!-- Column 2 -->
    <text x="140" y="0" class="stat-label">Pull Requests</text>
    <text x="140" y="22" class="stat-value">{{.PRs}}</text>
    
    <text x="140" y="55" class="stat-label">Reviews</text>
    <text x="140" y="77" class="stat-value">{{.Reviews}}</text>
    
    <text x="140" y="110" class="stat-label">Total Stars</text>
    <text x="140" y="132" class="stat-value">{{.Stars}}</text>

    <!-- Column 3 (Issues) -->
    <text x="280" y="0" class="stat-label">Issues</text>
    <text x="280" y="22" class="stat-value">{{.Issues}}</text>

    <text x="280" y="55" class="stat-label">Private Contribs</text>
    <text x="280" y="77" class="stat-value">{{.Private}}</text>
  </g>

  <!-- Detailed Language Breakdown -->
  <g transform="translate(35, 230)">
    <text x="0" y="0" class="stat-label">Language Activity Breakdown</text>
    <rect x="0" y="12" width="380" height="8" rx="4" fill="#333" />
    <g transform="translate(0, 12)">
      {{range $i, $lang := .Languages}}
        <rect x="{{$lang.Offset}}" y="0" width="{{$lang.Width}}" height="8" fill="{{$lang.Color}}" {{if eq $i 0}}rx="4"{{end}} />
      {{end}}
    </g>
    
    <!-- Top 3 Detail List -->
    <g transform="translate(0, 40)">
      {{range $i, $lang := .Languages}}
        {{if lt $i 3}}
        <g transform="translate(0, {{mul $i 20}})">
          <circle cx="4" cy="0" r="4" fill="{{$lang.Color}}" />
          <text x="15" y="4" class="lang-label">{{$lang.Name}}</text>
          <text x="380" y="4" class="lang-value" style="text-anchor: end;">{{$lang.LineCount}} lines ({{$lang.Percent}}%)</text>
        </g>
        {{end}}
      {{end}}
      {{if gt (len .Languages) 3}}
      <g transform="translate(0, 60)">
          <circle cx="4" cy="0" r="4" fill="#666" />
          <text x="15" y="4" class="lang-label">Others</text>
          <text x="380" y="4" class="lang-value" style="text-anchor: end;">{{.OtherLines}} lines</text>
      </g>
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
	ActiveDays  string
	Private     string
	OtherLines  string
	Languages   []SVGLang
	AccentColor string
	TextColor   string
	BgColor     string
	BorderColor string
}

type SVGLang struct {
	Name      string
	Size      int64
	Color     string
	Width     float64
	Offset    float64
	LineCount string
	Percent   string
}

// Add useful template functions
func Mul(a, b int) int { return a * b }
func Add(a, b int) int { return a + b }
