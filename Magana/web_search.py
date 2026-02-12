import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
SERPER_KEY = os.getenv("SERPER_API_KEY")
SERPER_TIMEOUT_SECONDS = float(os.getenv("SERPER_TIMEOUT_SECONDS", "6"))

_SEARCH_CACHE = {}
_SESSION = requests.Session()


def _get_cached_result(cache_key, cache_ttl_seconds):
    cached_entry = _SEARCH_CACHE.get(cache_key)
    if not cached_entry:
        return None

    created_at, payload = cached_entry
    if time.time() - created_at > cache_ttl_seconds:
        _SEARCH_CACHE.pop(cache_key, None)
        return None

    return payload


def search_web(query, max_results=3, cache_ttl_seconds=120):
    """
    Searches Google via Serper.dev API.
    Uses a short-lived in-memory cache to reduce repeated API round-trips.
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return None

    cache_key = (cleaned_query.lower(), int(max_results))
    cached_payload = _get_cached_result(cache_key, cache_ttl_seconds)
    if cached_payload:
        return cached_payload

    url = "https://google.serper.dev/search"

    payload = json.dumps({
        "q": cleaned_query,
        "num": max_results,
    })

    headers = {
        "X-API-KEY": SERPER_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = _SESSION.post(
            url,
            headers=headers,
            data=payload,
            timeout=SERPER_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            print(f"Serper API Error: {response.text}")
            return None

        data = response.json()

        if "organic" not in data:
            return None

        results = data["organic"]

        context_str = "WEB SEARCH RESULTS (Use these facts to answer):\n"
        for res in results:
            title = res.get("title", "No Title")
            snippet = res.get("snippet", "No content.")
            link = res.get("link", "#")
            date = res.get("date", "")

            context_str += (
                f"- Title: {title}\n"
                f"  Date: {date}\n"
                f"  Snippet: {snippet}\n"
                f"  Link: {link}\n\n"
            )

        _SEARCH_CACHE[cache_key] = (time.time(), context_str)
        return context_str

    except Exception as e:
        print(f"Search Connection Error: {e}")
        return None


if __name__ == "__main__":
    print(search_web("Current President of Ghana"))
