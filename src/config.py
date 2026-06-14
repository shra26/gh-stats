# config.py -- module-level constants shared across all card handlers and fetchers.
# Import as: from config import GITHUB_GRAPHQL_URL, ...

GITHUB_GRAPHQL_URL: str = "https://api.github.com/graphql"
GITHUB_REST_SEARCH_COMMITS_URL: str = "https://api.github.com/search/commits"

# Name of the environment variable that holds the SSM parameter name for PATs.
SSM_PAT_PARAM_ENV: str = "SSM_PAT_PARAM"

# Name of the environment variable holding a comma-separated username allowlist.
WHITELIST_ENV: str = "GH_WHITELIST"

# Optional global override for cache TTL (seconds). When set, overrides per-card resolution.
CACHE_SECONDS_ENV: str = "CACHE_SECONDS"

# Card width constants (pixels) used by SVG renderers.
RANK_CARD_MIN_WIDTH: int = 420
RANK_CARD_DEFAULT_WIDTH: int = 450
RANK_ONLY_CARD_MIN_WIDTH: int = 290
RANK_ONLY_CARD_DEFAULT_WIDTH: int = 290
