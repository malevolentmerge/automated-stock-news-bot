import os
import time
import re
import json
import requests
import feedparser
from google import genai
from google.genai import types
from datetime import datetime, timezone
from newspaper import Article, Config
from typing import List, Dict

# --- CONFIGURATION ---
TICKERS = ["AAPL", "MSFT", "GOOG", "META", "AMZN", "COST", "NFLX", "VTI"]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Initialize Gemini
if GEMINI_API_KEY:
    client = genai.Client()
else:
    raise ValueError("Missing GEMINI_API_KEY environment variable")

# --- CORE FUNCTIONS ---

def fetch_rss_headlines(tickers: List[str]) -> Dict[str, Dict]:
    """Fetches RSS headlines filtered strictly by current Year-Month-Day."""
    
    # Get current date (UTC) as a date object: YYYY-MM-DD
    # Using datetime.now(timezone.utc) is the modern standard
    today_date = datetime.now(timezone.utc).date()
    
    print(f"Scanning feeds for date: {today_date}")
    headline_map = {}

    for ticker in tickers:
        feed_url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
        feed = feedparser.parse(feed_url)
        
        for index, entry in enumerate(feed.entries):
            # 1. Skip if no date info exists
            if not hasattr(entry, 'published_parsed'):
                continue
            
            # 2. Convert time_struct to date object (removes hours/mins/secs)
            # time.mktime converts struct to seconds, fromtimestamp makes it a datetime
            pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed)).date()

            # 3. Direct comparison: Year, Month, and Day match only
            if pub_date == today_date:
                unique_id = f"{ticker}_{index}"
                headline_map[unique_id] = {
                    "id": unique_id, 
                    "ticker": ticker, 
                    "title": entry.title, 
                    "link": entry.link,
                    "date_str": pub_date.isoformat() # Stores as "2026-02-07"
                }
    
    print(f"Found {len(headline_map)} articles published on {today_date}.")
    return headline_map

def identify_priority_stories(headline_map: Dict[str, Dict]) -> List[str]:
    """Uses Gemini to filter the list down to the most critical IDs."""
    
    # Create a simplified list for the LLM to read (saves tokens)
    headlines_minified = [
        {'id': data['id'], 'title': data['title']} 
        for data in headline_map.values()
    ]

    prompt = f"""
    Act as a senior stock analyst. From the following list, pick the top 10 most critical, 
    market-moving news items. Focus on earnings, legal issues, or major product shifts.
    Return ONLY a JSON list of the IDs.
    
    HEADLINES:
    {json.dumps(headlines_minified)}
    """
    
    try:
        response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=list[str],   # 🔥 forces valid JSON array of strings
                    temperature=0.2
                )
            )
        
        return response.parsed
    except Exception as e:
        print(f"AI Filter failed, falling back to recent headlines: {e}")
        # Fallback: Return the first 5 IDs from the map
        return list(headline_map.keys())[:5]

def scrape_article_content(url: str) -> str:
    """Helper function to download and parse a single article."""
    config = Config()
    config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    config.request_timeout = 10
    
    try:
        article = Article(url, config=config)
        article.download()
        article.parse()

        text = article.text
        if len(text) > 5000:
            cutoff = text.rfind('.', 0, 5000)
            text = text[:cutoff+1] if cutoff != -1 else text[:5000]
        return text
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        return ""

def compile_news_brief(priority_ids: List[str], headline_map: Dict[str, Dict]) -> str:
    """Scrapes validated winners and formats them into a single context string."""
    full_context = ""

    for item_id in priority_ids:
        if item_id not in headline_map:
            continue
            
        story = headline_map[item_id]
        content = scrape_article_content(story['link'])
        
        if content:
            full_context += (
                f"\n[STOCK: {story['ticker']}] TITLE: {story['title']}\n"
                f"CONTENT: {content}\n"
            )
            
    return full_context

def generate_discord_summary(news_context: str) -> str:
    """Generates a professional Discord-ready stock summary."""

    prompt = f"""
    You are a senior equity analyst writing a quick market brief for professional investors.
    Summarize the following news articles into a concise, scannable Discord post. Follow these rules:

    - Use bold headers for the company/ticker: **AAPL**  
    - Include 1–2 sentences per headline summarizing the key point
    - Include sentiment in parentheses: (Bullish / Neutral / Bearish)
    - Focus on earnings, legal issues, product launches, or major market-moving events
    - Maximum 5–6 lines per ticker
    - Do NOT add commentary, jokes, or extra fluff
    - Keep it very short and fast to read — this is for daily professional reading

    NEWS ARTICLES:
    {news_context}
    """

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )
        return response.text
    except Exception as e:
        print(f"An error occured with AI summary: {e}")
        return "Something went wrong... no stock news summary today!"

def send_to_discord(text: str):
    """Splits the text into chunks and posts to the webhook."""
    if not DISCORD_WEBHOOK_URL:
        print("No Discord Webhook URL provided.")
        return

    # Split by sentences, ensuring chunks are under 2000 chars
    sentences = re.split(r'(?<=[.!?]) +', text)
    messages = []
    current_message = "📊 **Daily Portfolio Briefing**\n\n"
    
    for sentence in sentences:
        if len(current_message) + len(sentence) > 1900:
            messages.append(current_message.strip())
            current_message = "*(Continued...)*\n" + sentence + " "
        else:
            current_message += sentence + " "
    messages.append(current_message.strip())

    for msg in messages:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
        time.sleep(1)

# --- MAIN EXECUTION FLOW ---

def main():
    # 1. Fetch
    headlines_map = fetch_rss_headlines(TICKERS)
    if not headlines_map:
        print("No headlines found.")
        return

    # 2. Filter
    priority_ids = identify_priority_stories(headlines_map)
    print(priority_ids)
    
    # 3. Scrape
    context_data = compile_news_brief(priority_ids, headlines_map)
    
    if not context_data:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": "🌙 No significant market-moving news found today."})
        return

    # 4. Summarize
    final_summary = generate_discord_summary(context_data)
    print(final_summary)

    # 5. Notify
    send_to_discord(final_summary)
    print("Completed!")

if __name__ == "__main__":
    main()