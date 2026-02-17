# Life Dashboard (Streamlit Version)

A personal dashboard built with Streamlit that consolidates weather, stocks, news, mood tracking, decision logging, ideas vault, task management, and activity visualization into a single, mobile-friendly interface.

## Features

- **Dashboard Home**: Weather, sobriety counter, system info
- **News**: General/Tech+AI/Market tabs with RSS feeds
- **Stocks**: Real-time Finnhub quotes organized by category
- **Mood Tracker**: Emoji-based mood tracking with history and charts
- **Decision Log**: Log important decisions with context
- **Ideas Vault**: Capture and store ideas
- **Tasks**: Notion + Todoist + Kimi's TODOs integration
- **Activity**: Session heatmap visualization

## Requirements

```
streamlit>=1.30
requests>=2.31
feedparser>=6.0
psutil>=5.9
altair>=5.0
pandas>=2.0
```

## Setup

1. **Install dependencies**:
   ```bash
   cd life-dashboard-streamlit
   pip install -r requirements.txt
   ```

2. **Configure API Keys**:

   Create or edit `~/.openclaw/.env` and add:
   ```
   FINNHUB_API_KEY=your_finnhub_key
   NOTION_API_KEY=your_notion_key
   TODOIST_API_KEY=your_todoist_key
   ```

   Get your API keys:
   - **Finnhub**: https://finnhub.io/
   - **Notion**: https://www.notion.so/my-integrations
   - **Todoist**: https://todoist.com/app_settings/integrations

3. **Run the app**:
   ```bash
   streamlit run streamlit_app.py
   ```

4. **Access**: Open http://localhost:8501 in your browser

## Password

Default password: `nick123`

Change in `streamlit_app.py`:
```python
APP_PASSWORD = "your_new_password"
```

## Data Files

The app uses these data files from the workspace:
- Mood data: `/home/openclaw/.openclaw/workspace/webapp/data/mood_data.json`
- Decisions: `/home/openclaw/.openclaw/workspace/webapp/data/decisions.json`
- Ideas: `/home/openclaw/.openclaw/workspace/webapp/data/ideas.json`
- AA Meetings: `/home/openclaw/.openclaw/workspace/webapp/data/aa_meetings.json`
- Kimi's TODOs: `/home/openclaw/.openclaw/workspace/kimi_todos.md`

## Deployment

### Option 1: Local Development
```bash
streamlit run streamlit_app.py --server.port 8501
```

### Option 2: Systemd Service (Linux)

Create `/etc/systemd/system/life-dashboard.service`:
```ini
[Unit]
Description=Life Dashboard Streamlit
After=network.target

[Service]
Type=simple
User=openclaw
WorkingDirectory=/home/openclaw/.openclaw/workspace/life-dashboard-streamlit
ExecStart=/usr/bin/streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable life-dashboard
sudo systemctl start life-dashboard
```

## Mobile Access

The app is mobile-responsive. Access via:
- Local network: `http://<server-ip>:8501`
- SSH tunnel (for remote access):
  ```bash
  ssh -L 8501:localhost:8501 root@167.172.247.151
  ```

## Tech Stack

- **Streamlit**: Web framework
- **Pandas/Altair**: Data visualization
- **Feedparser**: RSS news feeds
- **Finnhub API**: Stock quotes
- **Notion API**: Task management
- **Todoist REST API**: Task management

## License

Personal use only.
