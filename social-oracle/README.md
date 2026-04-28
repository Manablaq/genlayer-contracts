# SocialOracle

> Hacker News on-chain — live tech news cached through validator consensus with AI trend analysis.

---

## Overview

SocialOracle is a GenLayer Intelligent Contract that brings Hacker News data on-chain. It monitors three story feeds — top, new, and best-rated — fetching the top 10 stories per feed through five-validator consensus. The AI methods use GenLayer's native LLM to generate plain-English tech trend briefings and topic-specific analysis directly inside the contract.

No API key required. Hacker News Firebase API is confirmed compatible with GenLayer validators.

---

## Story Feeds

| Feed | Method | Description |
|---|---|---|
| Top Stories | `fetch_trending` | Currently highest-ranked stories |
| New Stories | `fetch_latest` | Most recently submitted stories |
| Best Stories | `fetch_top_rated` | All-time best-rated stories |

---

## Methods

### Write Methods
Fetch live data and write to chain. Require gas and validator consensus.

| Method | Parameters | Description |
|---|---|---|
| `fetch_trending` | — | Fetch and cache top stories |
| `fetch_latest` | — | Fetch and cache newest stories |
| `fetch_top_rated` | — | Fetch and cache best-rated stories |
| `generate_briefing` | — | AI one-sentence tech trend summary |
| `analyse_topic` | `topic: str` | AI analysis of a specific topic across all feeds |

### Read Methods
Read from cache. No gas required.

| Method | Parameters | Description |
|---|---|---|
| `read_feed` | `feed: str` | One cached feed: "trending", "latest", "top_rated" |
| `read_all` | — | All cached feeds and AI outputs |
| `top_commented` | — | Story with the most comments |
| `top_scored` | — | Story with the highest score |
| `search` | `keyword: str` | Search all cached stories by keyword |
| `freshness` | — | Whether the cache has been populated |
| `cache_report` | — | Status of all three feeds |

---

## Deploying

1. Open [studio.genlayer.com](https://studio.genlayer.com)
2. Paste `contract.py` into the editor
3. Click **Deploy new instance** — no parameters needed
4. Wait for FINALIZED

---

## Testing

```
# Step 1 — fetch stories (required before AI methods)
fetch_trending()

# Step 2 — generate AI briefing
generate_briefing()
# Returns one sentence: what is tech talking about right now?

# Step 3 — read everything
read_all()

# Fetch other feeds
fetch_latest()
fetch_top_rated()

# Search across all cached feeds
search("AI")
search("rust")
search("blockchain")

# Analyse a specific topic (must appear in cached stories)
analyse_topic("AI")

# Surface top stories
top_scored()
top_commented()

# Check cache status
cache_report()
```

---

## Data Source

Hacker News Firebase API (`hacker-news.firebaseio.com`) — free, no API key, confirmed working with GenLayer validators. Fetches story ID, title, score, comment count, URL, and author for each story.

---

## How Consensus Works

Story fetches use `prompt_comparative` requiring at least 2-3 shared titles between validators. Because rankings shift in real time, validators fetching moments apart may see slightly different lists — the tolerance accounts for this.

`generate_briefing` uses `prompt_comparative` with a lenient condition: two summaries are equivalent if they mention at least one similar tech topic and are both one sentence. Minor wording differences are explicitly acceptable.

`analyse_topic` uses `prompt_comparative` requiring validators to identify the same key themes in their analysis.

---

## State

| Variable | Type | Purpose |
|---|---|---|
| `store` | `str` | JSON cache of stories and AI outputs |
| `pulse` | `str` | Last fetch status |