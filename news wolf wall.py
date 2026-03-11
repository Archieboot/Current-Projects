#News Scan
import requests
from anthropic import Anthropic

NEWS_API_KEY = "YOUR_NEWSAPI_KEY"
ANTHROPIC_API_KEY = "YOUR_ANTHROPIC_API_KEY"

client = Anthropic(api_key=ANTHROPIC_API_KEY)

def fetch_news():
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "language": "en",
        "pageSize": 30,
        "apiKey": NEWS_API_KEY,
        "category": "business"
    }
    response = requests.get(url, params=params)
    articles = response.json().get("articles", [])
    
    headlines = []
    for a in articles:
        title = a.get("title", "")
        description = a.get("description", "")
        if title:
            headlines.append(f"- {title}: {description}")
    
    return "\n".join(headlines)

def get_briefing(headlines):
    prompt = f"""Here are today's top business and finance headlines:
{headlines}

You are helping a finance student prepare for interviews and market conversations. 
Your job is not to summarise the news — it is to extract what matters for someone 
who needs to speak intelligently about markets, macro, and the economy.
Pick the most important and substantive story for someone entering finance. 

For the significant story:
- Explain the core mechanics (why does this actually matter economically?)
- Connect it to broader themes (interest rates, inflation, credit cycles, sector dynamics)
- Flag any second-order effects or relationships a sharp interviewer might probe
- Note the Australian angle where relevant — RBA implications, ASX exposure, AUD impact
- Flag any valuation implications — how does this move multiples, discount rates, or sector positioning?
- If it's a deal, distress situation, or capital markets story — explain the structure and what it signals
One story done properly beats three done shallowly.

At the end of the story add:
INTERVIEW ANGLE: One sharp question an interviewer might ask about this story, 
and a model one-paragraph answer a candidate should be able to give.

Target audience: final year finance/economics students interviewing for graduate 
roles in investment banking, private equity, asset management, or economic consulting.

Skip anything that isn't substantive. Prioritise depth over breadth — 3 well-explained 
stories beat 10 shallow ones.

Write as if briefing someone 30 minutes before a markets interview."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text

def get_news_script(briefing):
    prompt = f"""Here is a finance and markets briefing:

{briefing}

Rewrite this as Jordan Belfort explaining the day's markets directly to you — 
as if he's pulled you aside to break it down.

Rules:
- Opening line grabs attention immediately — Belfort never eases in
- He explains every concept fully and correctly — all the mechanics, second-order 
  effects, and market implications must be preserved from the briefing
- Uses Belfort's actual phrasing — "let me tell you something", "here's the thing 
  nobody's talking about", "and I'm telling you right now", "listen to me carefully"
- Builds each story like a pitch — sets the scene, explains the stakes, lands the point
- Occasional aside that makes it feel live and unscripted — like he just thought of 
  a better analogy mid-sentence
- Confident, slightly conspiratorial tone — like he's giving you information most 
  people don't have access to
- Never dumbs it down — Belfort respects people who can keep up
- Aim for 500 words or less.
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text

def main():
    print("Fetching today's news...\n")
    headlines = fetch_news()
    
    print("=== FINANCE BRIEFING ===\n")
    briefing = get_briefing(headlines)
    print(briefing)
    
    print("\n=== NEWS SCRIPT ===\n")
    script = get_news_script(briefing)
    print(script)

if __name__ == "__main__":
    main()
