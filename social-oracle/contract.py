# { "Depends": "py-genlayer:test" }

from genlayer import *
import json
import typing

HN_API = "https://hacker-news.firebaseio.com/v0"


def _pull_stories(feed: str, limit: int = 10) -> str:
    try:
        ids_raw = gl.nondet.web.render(
            f"{HN_API}/{feed}stories.json",
            mode="text"
        )
        if not ids_raw or ids_raw.strip() in ["null", "", "null\n"]:
            return json.dumps({"error": "Hacker News API is down.", "status": "unavailable"})

        ids = json.loads(ids_raw)
        if not isinstance(ids, list) or len(ids) == 0:
            return json.dumps({"error": "Hacker News API is down.", "status": "unavailable"})

        items = []
        for story_id in ids[:limit]:
            raw = gl.nondet.web.render(f"{HN_API}/item/{story_id}.json", mode="text")
            if not raw or raw.strip() == "null":
                continue
            s = json.loads(raw)
            if not s:
                continue
            items.append({
                "id":       s.get("id"),
                "title":    s.get("title", "No title"),
                "score":    s.get("score", 0),
                "comments": s.get("descendants", 0),
                "url":      s.get("url", ""),
                "author":   s.get("by", "unknown"),
            })

        if not items:
            return json.dumps({"error": "Hacker News API is down.", "status": "unavailable"})

        return json.dumps({
            "source":      "Hacker News",
            "feed":        feed,
            "total":       len(items),
            "status":      "ok",
            "items":       items,
        }, sort_keys=True)

    except Exception:
        return json.dumps({"error": "Hacker News API is down.", "status": "unavailable"})


class SocialOracle(gl.Contract):

    store:   str
    pulse:   str

    def __init__(self):
        self.store = "{}"
        self.pulse = "never"

    # ── FETCH ───────────────────────────────────────────────────────

    @gl.public.write
    def fetch_trending(self) -> typing.Any:
        def fetch() -> str:
            return _pull_stories("top", 10)

        fresh              = gl.eq_principle.prompt_comparative(
            fetch,
            "The outputs represent top stories from Hacker News. "
            "They are equivalent if both show an API error, "
            "or if they share at least 3 of the same story titles."
        )
        data               = json.loads(self.store)
        data["trending"]   = json.loads(fresh)
        self.store         = json.dumps(data, sort_keys=True)
        self.pulse         = "updated"

    @gl.public.write
    def fetch_latest(self) -> typing.Any:
        def fetch() -> str:
            return _pull_stories("new", 10)

        fresh            = gl.eq_principle.prompt_comparative(
            fetch,
            "The outputs represent new stories from Hacker News. "
            "They are equivalent if both show an API error, "
            "or if they share at least 2 of the same story titles or IDs."
        )
        data             = json.loads(self.store)
        data["latest"]   = json.loads(fresh)
        self.store       = json.dumps(data, sort_keys=True)
        self.pulse       = "updated"

    @gl.public.write
    def fetch_top_rated(self) -> typing.Any:
        def fetch() -> str:
            return _pull_stories("best", 10)

        fresh              = gl.eq_principle.prompt_comparative(
            fetch,
            "The outputs represent best stories from Hacker News. "
            "They are equivalent if both show an API error, "
            "or if they share at least 3 of the same story titles."
        )
        data               = json.loads(self.store)
        data["top_rated"]  = json.loads(fresh)
        self.store         = json.dumps(data, sort_keys=True)
        self.pulse         = "updated"

    # ── AI ─────────────────────────────────────────────────────────

    @gl.public.write
    def generate_briefing(self) -> typing.Any:
        data = json.loads(self.store)
        if "trending" not in data:
            raise gl.vm.UserError("No stories cached. Call fetch_trending first.")

        titles = [s["title"] for s in data["trending"].get("items", [])]

        def summarize() -> str:
            prompt = (
                f"Based on these Hacker News top story titles, write ONE sentence "
                f"summarizing the biggest tech trends right now:\n\n"
                f"{json.dumps(titles)}\n\n"
                f"Respond with only the summary sentence, nothing else."
            )
            return gl.nondet.exec_prompt(prompt)

        briefing              = gl.eq_principle.prompt_comparative(
            summarize,
            "Both outputs summarize tech news from the same story titles. "
            "They are equivalent if both are one sentence and mention at least "
            "one similar tech topic. Minor wording differences are acceptable."
        )
        data["briefing"]      = briefing
        self.store            = json.dumps(data, sort_keys=True)

    @gl.public.write
    def analyse_topic(self, topic: str) -> typing.Any:
        data = json.loads(self.store)
        all_titles = []
        for feed in ["trending", "latest", "top_rated"]:
            if feed in data:
                for s in data[feed].get("items", []):
                    if topic.lower() in s.get("title", "").lower():
                        all_titles.append(s["title"])

        if not all_titles:
            raise gl.vm.UserError("No stories found about " + topic + " in cache.")

        def analyze() -> str:
            prompt = (
                f"Based on these Hacker News story titles about '{topic}', "
                f"write two sentences analyzing the current discussion around this topic:\n\n"
                f"{json.dumps(all_titles)}\n\n"
                f"Respond with only the analysis, nothing else."
            )
            return gl.nondet.exec_prompt(prompt)

        analysis                    = gl.eq_principle.prompt_comparative(
            analyze,
            "Both outputs analyze the same topic from the same stories. "
            "They are equivalent if they identify the same key themes."
        )
        data["analysis_" + topic]   = {"topic": topic, "analysis": analysis, "stories_found": len(all_titles)}
        self.store                  = json.dumps(data, sort_keys=True)

    # ── READ ───────────────────────────────────────────────────────

    @gl.public.view
    def read_feed(self, feed: str) -> str:
        data = json.loads(self.store)
        if feed in data:
            return json.dumps(data[feed])
        return json.dumps({"error": feed + " not cached. Use: trending, latest, top_rated."})

    @gl.public.view
    def read_all(self) -> str:
        return self.store

    @gl.public.view
    def top_commented(self) -> str:
        data = json.loads(self.store)
        if "trending" not in data:
            return json.dumps({"error": "No stories cached. Call fetch_trending first."})
        items = data["trending"].get("items", [])
        if not items:
            return json.dumps({"error": "No stories available."})
        winner = max(items, key=lambda s: s.get("comments", 0))
        return json.dumps(winner)

    @gl.public.view
    def top_scored(self) -> str:
        data = json.loads(self.store)
        if "trending" not in data:
            return json.dumps({"error": "No stories cached. Call fetch_trending first."})
        items = data["trending"].get("items", [])
        if not items:
            return json.dumps({"error": "No stories available."})
        winner = max(items, key=lambda s: s.get("score", 0))
        return json.dumps(winner)

    @gl.public.view
    def search(self, keyword: str) -> str:
        data    = json.loads(self.store)
        results = []
        kw      = keyword.lower()
        for feed in ["trending", "latest", "top_rated"]:
            if feed not in data:
                continue
            for s in data[feed].get("items", []):
                if kw in s.get("title", "").lower():
                    entry         = dict(s)
                    entry["feed"] = feed
                    results.append(entry)
        if not results:
            return json.dumps({"error": "No stories found matching '" + keyword + "'."})
        return json.dumps({"keyword": keyword, "count": len(results), "results": results})

    @gl.public.view
    def freshness(self) -> str:
        if self.pulse == "never":
            return json.dumps({"fresh": False, "reason": "Cache has never been populated."})
        return json.dumps({"fresh": True, "reason": "Cache has been populated.", "status": self.pulse})

    @gl.public.view
    def cache_report(self) -> str:
        data   = json.loads(self.store)
        feeds  = ["trending", "latest", "top_rated"]
        report = []
        for feed in feeds:
            if feed in data:
                d = data[feed]
                report.append({
                    "feed":   feed,
                    "cached": True,
                    "total":  d.get("total", 0) if isinstance(d, dict) else 0,
                    "status": d.get("status", "unknown") if isinstance(d, dict) else "unknown",
                })
            else:
                report.append({"feed": feed, "cached": False})
        return json.dumps({"pulse": self.pulse, "feeds": report})