import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
SERPER_KEY = os.getenv("SERPER_API_KEY")

def search_web(query, max_results=3):
    """
    Searches Google via Serper.dev API.
    """
    url = "https://google.serper.dev/search"
    
    payload = json.dumps({
        "q": query,
        "num": max_results # Ask for specific number of results
    })
    
    headers = {
        'X-API-KEY': SERPER_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        
        if response.status_code != 200:
            print(f"Serper API Error: {response.text}")
            return None
            
        data = response.json()
        
        # specific check for 'organic' results (standard search results)
        if "organic" not in data:
            return None
            
        results = data["organic"]
        
        context_str = "WEB SEARCH RESULTS (Use these facts to answer):\n"
        for res in results:
            title = res.get('title', 'No Title')
            snippet = res.get('snippet', 'No content.')
            link = res.get('link', '#')
            date = res.get('date', '') # Serper often provides dates for news
            
            context_str += f"- Title: {title}\n  Date: {date}\n  Snippet: {snippet}\n  Link: {link}\n\n"
            
        return context_str

    except Exception as e:
        print(f"Search Connection Error: {e}")
        return None

# --- TEST BLOCK ---
if __name__ == "__main__":
    print(search_web("Current President of Ghana"))