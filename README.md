Automation Tools
Python scripts built to automate repetitive tasks.

Scripts
ord_minnett_automation.py
Automates the processing of broker contract notes from a shared Outlook inbox.

Connects to a shared Microsoft 365 mailbox via the Graph API
Filters emails by broker sender
Downloads PDF attachments
Extracts key fields from each PDF (confirmation date, client name, platform, account number, company, transaction type) using text parsing
Renames files to a consistent naming convention
Saves to a local folder
Archives processed emails automatically

Dependencies: pypdf, msal, requests

news_wolf_wall.py
Automated daily finance briefing tool for interview preparation and market awareness.

Fetches top business headlines via NewsAPI
Uses the Anthropic API to generate a deep-dive briefing on the most market-relevant story — covering macro mechanics, second-order effects, valuation implications, and Australian market angle
Reformats the briefing into an engaging script for easier consumption
Includes an interview question and model answer for each story

Dependencies: requests, anthropic

Setup

Clone the repo
Install dependencies: pip install pypdf msal requests anthropic
Fill in your API credentials in the config section at the top of each script
Run: python script_name.py
