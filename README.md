# gh-stats

Self-hosted GitHub readme stats cards on AWS Lambda + CloudFront, written in Python.

A Python reimplementation of [anuraghazra/github-readme-stats](https://github.com/anuraghazra/github-readme-stats), deployed on your own AWS infrastructure.

## Why self-host?

The public `github-readme-stats.vercel.app` instance shares a single GitHub API quota across thousands of users and frequently returns broken-image error cards ("Maximum retries exceeded"). Running your own instance with your own GitHub PAT gives you a private rate-limit bucket (5000 req/hr), full control over caching, and zero dependency on a third-party service.

---

## Cards

Replace `USERNAME` with a GitHub username and `REPO` with a repo name. All card URLs go through `https://gh-stats.shravanthv.com`.

### Stats card

```markdown
![GitHub Stats](https://gh-stats.shravanthv.com/api?username=USERNAME&theme=tokyonight&show_icons=true)
```

### Top languages

```markdown
![Top Languages](https://gh-stats.shravanthv.com/api/top-langs?username=USERNAME&layout=compact)
```

### Repo pin

```markdown
![Repo Pin](https://gh-stats.shravanthv.com/api/pin?username=USERNAME&repo=REPO)
```

### Gist pin

```markdown
![Gist Pin](https://gh-stats.shravanthv.com/api/gist?id=GIST_ID)
```

### WakaTime stats

```markdown
![WakaTime](https://gh-stats.shravanthv.com/api/wakatime?username=USERNAME)
```

---

## Parameters

Parameters are passed as query strings. Color values are **hex without a leading `#`** (e.g. `bg_color=1a1b27`, not `#1a1b27`).

| Parameter | Description | Example |
|---|---|---|
| `theme` | Named color theme | `tokyonight`, `dark`, `radical`, `gruvbox` |
| `hide` | Comma-separated stats to omit | `stars,commits,prs,issues,contribs` |
| `hide_border` | Remove card border | `true` |
| `hide_title` | Remove card title | `true` |
| `show_icons` | Show stat icons (stats card) | `true` |
| `title_color` | Title hex color | `e7a900` |
| `icon_color` | Icon hex color | `f78166` |
| `text_color` | Body text hex color | `c9d1d9` |
| `bg_color` | Background color or gradient | `161b22` or `45,1a1b27,2d2d44` |
| `border_color` | Border hex color | `30363d` |
| `layout` | Card layout variant | `compact`, `donut`, `pie` |
| `langs_count` | Number of languages shown | `6` |
| `cache_seconds` | Override cache TTL | `86400` |
| `locale` | Card language locale | `en`, `de`, `zh-cn` |
| `border_radius` | Corner radius in px | `10` |
| `custom_title` | Override card title | `My+Stats` |

`bg_color` gradients use the format `angle,color1,color2,...` (e.g. `45,1a1b27,2d2d44` for a 45-degree two-stop gradient). See the plan document for the full parameter list per card type.

---

## Architecture

```
Browser / GitHub Camo
        |
    CloudFront (CDN, TLS, per-card cache TTLs, WAF)
        | OAC SigV4
   Lambda Function URL (AWS_IAM - private)
        |
   Python 3.12 arm64 handler
        |
  GitHub GraphQL / REST API  +  WakaTime API
```

- **Single Lambda** (256 MB, 10 s timeout, arm64) routes all five card types internally.
- **CloudFront OAC** signs every request with SigV4 - the raw Function URL is private (direct hits return 403).
- **Per-card cache TTLs**: stats 1d, top-langs 6d, pin 10d, gist 2d, wakatime 1d, error 10 min.
- **Errors always return 200** with an error-card SVG (`max-age=600`) so GitHub Camo never shows a broken image.
- **GitHub PATs** are stored in SSM Parameter Store as SecureString (KMS-encrypted). Never in env vars or tfstate.
- **Security**: username allowlist (`GH_WHITELIST` env var), Lambda reserved concurrency cap, AWS WAF rate-based rules, CloudFront param whitelist cache policy.

---

## Local development

Set a GitHub token, then start the local dev server:

```bash
export GH_TOKEN=ghp_xxx
python local/serve.py
```

Open `http://localhost:8000/api?username=YOU&theme=dark` in your browser.

The local server synthesizes a Lambda v2 event and calls the handler directly - no AWS needed.

---

## Deploy

### 1. Store your GitHub PAT in SSM

```bash
aws ssm put-parameter \
  --name /gh-stats/pats \
  --type SecureString \
  --value 'ghp_xxx' \
  --overwrite \
  --profile website-handler
```

### 2. Provision infrastructure with Terraform

```bash
cd terraform
terraform init
terraform apply
```

CloudFront provisioning takes roughly 5-10 minutes on first apply. Subsequent Lambda-only updates skip the CloudFront wait - deploy directly with `aws lambda update-function-code` to iterate faster.

---

## Tests

```bash
pytest
```

Tests are unit-only (no network). Fixtures with canned GraphQL responses live in `tests/fixtures/`. `pyproject.toml` configures `pythonpath = ["src"]` so imports like `from rank import calculate_rank` work without any install step.

---

## Credits and license

Inspired by [anuraghazra/github-readme-stats](https://github.com/anuraghazra/github-readme-stats). This is an independent reimplementation in Python with a different deployment model; no code was copied from the original.

MIT License - see [LICENSE](LICENSE).
