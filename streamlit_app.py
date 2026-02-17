#!/usr/bin/env python3
"""
Life Dashboard - Streamlit Version
Converted from Flask app with all features
"""

import streamlit as st
import requests
import json
import os
import psutil
import feedparser
import urllib.request
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict
import pandas as pd
import altair as alt

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load environment variables from ~/.openclaw/.env
env_file = Path.home() / '.openclaw' / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# API Keys
NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '287cb484-7040-45cd-a44b-315dddbcd010')
TODOIST_API_KEY = os.environ.get('TODOIST_API_KEY', '')
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', '')

# File paths
MOOD_DATA_FILE = "/home/openclaw/.openclaw/workspace/webapp/data/mood_data.json"
DECISIONS_FILE = "/home/openclaw/.openclaw/workspace/webapp/data/decisions.json"
IDEAS_FILE = "/home/openclaw/.openclaw/workspace/webapp/data/ideas.json"
AA_MEETINGS_FILE = "/home/openclaw/.openclaw/workspace/webapp/data/aa_meetings.json"
AA_ATTENDED_FILE = "/home/openclaw/.openclaw/workspace/webapp/data/aa_attended.json"
KIMI_TODOS_FILE = "/home/openclaw/.openclaw/workspace/kimi_todos.md"
SESSIONS_DIR = "/home/openclaw/.openclaw/agents/main/sessions"

# Weather
WEATHER_LOCATION = "Sparta,NJ"
WEATHER_LAT = 41.03
WEATHER_LON = -74.64

# Password
APP_PASSWORD = "nick123"

# Stock categories
STOCK_CATEGORIES = {
    'Big Tech': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],
    'AI/Chips': ['NVDA', 'AMD', 'AVGO', 'QCOM', 'AMAT'],
    'Software': ['ADBE', 'CRM', 'ORCL', 'SNOW'],
    'Hardware': ['IBM', 'INTC', 'TXN'],
    'Speculative': ['PLTR', 'COIN', 'TTWO']
}

# RSS Feeds
RSS_FEEDS = {
    'general': [
        ('http://feeds.bbci.co.uk/news/world/rss.xml', 'BBC'),
        ('https://www.reutersagency.com/feed/?best-topics=news&post_type=best', 'Reuters'),
    ],
    'tech': [
        ('https://techcrunch.com/feed/', 'TechCrunch'),
        ('https://venturebeat.com/ai/feed/', 'VentureBeat AI'),
    ],
    'market': [
        ('https://finance.yahoo.com/news/rssindex', 'Yahoo Finance'),
    ]
}

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Life Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Password protection
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    """Show login screen if not authenticated"""
    if st.session_state.authenticated:
        return True
    
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 50px auto;
            padding: 30px;
            background-color: #262730;
            border-radius: 10px;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🔐 Life Dashboard")
    st.write("Please enter your password to access the app:")
    
    password = st.text_input("Password", type="password", key="login_password")
    
    if st.button("Login", key="login_button"):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    
    return False

if not check_password():
    st.stop()

# Custom dark theme CSS - Mobile responsive
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stSidebar {
        background-color: #262730;
    }
    .stTextInput, .stNumberInput, .stSelectbox, .stDateInput, .stTimeInput {
        background-color: #262730;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
    }
    .stButton>button {
        background-color: #4ade80;
        color: #0e1117;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #22c55e;
    }
    
    /* Mobile responsive */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        .stRadio > div {
            flex-direction: row !important;
            flex-wrap: wrap !important;
            justify-content: center;
        }
        div[data-testid="stRadio"] > div > label {
            padding: 8px 12px !important;
            margin: 4px !important;
            font-size: 0.8rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

@st.cache_data(ttl=60)
def get_system_info():
    """Get system info"""
    return {
        'cpu': psutil.cpu_percent(interval=1),
        'ram': psutil.virtual_memory().percent,
        'disk': psutil.disk_usage('/').percent
    }

@st.cache_data(ttl=900)
def fetch_weather():
    """Fetch weather from wttr.in and Open-Meteo"""
    eastern_zone = "America/New_York"
    
    WMO_ICONS = {
        0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️', 45: '🌫️', 48: '🌫️',
        51: '🌧️', 53: '🌧️', 55: '🌧️', 61: '🌧️', 63: '🌧️', 65: '🌧️',
        71: '❄️', 73: '❄️', 75: '❄️', 80: '🌧️', 81: '🌧️', 82: '🌧️',
        95: '⛈️', 96: '⛈️', 99: '⛈️'
    }
    
    WMO_DESCRIPTIONS = {
        0: 'Clear', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
        45: 'Fog', 48: 'Fog', 51: 'Drizzle', 53: 'Drizzle', 55: 'Dense drizzle',
        61: 'Rain', 63: 'Rain', 65: 'Heavy rain', 71: 'Snow', 73: 'Snow',
        75: 'Heavy snow', 80: 'Rain showers', 81: 'Rain showers', 82: 'Violent showers',
        95: 'Thunderstorm', 96: 'Thunderstorm', 99: 'Thunderstorm'
    }
    
    result = {'current': {}, 'forecast': []}
    
    # Try wttr.in first
    try:
        url = f"https://wttr.in/{WEATHER_LOCATION}?format=j1"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        current = data.get("current_condition", [{}])[0]
        result['current'] = {
            'temp': int(current.get("temp_F", 0)),
            'feels_like': int(current.get("FeelsLikeF", 0)),
            'humidity': int(current.get("humidity", 0)),
            'wind': int(current.get("windspeedMiles", 0)),
            'condition': current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
            'icon': '🌤️'
        }
    except Exception:
        # Fallback to Open-Meteo
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={WEATHER_LAT}&longitude={WEATHER_LON}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=America/New_York&temperature_unit=fahrenheit&wind_speed_unit=mph"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            current = data.get("current", {})
            result['current'] = {
                'temp': int(current.get("temperature_2m", 0)),
                'feels_like': int(current.get("temperature_2m", 0)),
                'humidity': int(current.get("relative_humidity_2m", 0)),
                'wind': int(current.get("wind_speed_10m", 0)),
                'condition': WMO_DESCRIPTIONS.get(current.get("weather_code", 0), "Unknown"),
                'icon': WMO_ICONS.get(current.get("weather_code", 0), '🌤️')
            }
        except Exception as e:
            result['current'] = {'error': str(e)}
    
    # Get forecast
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={WEATHER_LAT}&longitude={WEATHER_LON}&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=America/New_York&temperature_unit=fahrenheit"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        daily = data.get("daily", {})
        times = daily.get("time", [])[:7]
        max_temps = daily.get("temperature_2m_max", [])[:7]
        min_temps = daily.get("temperature_2m_min", [])[:7]
        codes = daily.get("weather_code", [])[:7]
        
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        for i, date_str in enumerate(times):
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            result['forecast'].append({
                'day': day_names[dt.weekday()],
                'high': int(round(max_temps[i])),
                'low': int(round(min_temps[i])),
                'icon': WMO_ICONS.get(codes[i], '☀️')
            })
    except Exception:
        pass
    
    return result

def get_sobriety_counter():
    """Calculate sobriety counter"""
    sobriety_date = date(2023, 6, 3)
    today = date.today()
    days_sober = (today - sobriety_date).days
    
    years = days_sober // 365
    remaining_days = days_sober % 365
    months = remaining_days // 30
    
    quotes = [
        ("The only thing that will keep us alcoholics from drinking is what we have learned about alcoholism.", "Bill W."),
        ("The greatest thing about sobriety is not having to wake up wondering what I did the night before.", "Dr. Bob"),
        ("AA is a gentle program for people who are desperately in need of a gentle program.", "Unknown"),
        ("One day at a time.", "AA Slogan"),
        ("We are not a glum little house. We have a right to be happy, joyous, and free.", "Bill W."),
        ("Keep it simple.", "AA Slogan"),
    ]
    
    quote_idx = today.timetuple().tm_yday % len(quotes)
    quote_text, quote_author = quotes[quote_idx]
    
    if years > 0:
        duration_text = f"~{years} year{'' if years == 1 else 's'}, {months} month{'' if months == 1 else 's'}"
    else:
        duration_text = f"~{months} month{'' if months == 1 else 's'}"
    
    return {
        'days': days_sober,
        'duration': duration_text,
        'quote': quote_text,
        'author': quote_author
    }

@st.cache_data(ttl=300)
def fetch_stocks():
    """Fetch stock quotes from Finnhub"""
    if not FINNHUB_API_KEY:
        return {'error': 'FINNHUB_API_KEY not configured'}
    
    result = {}
    
    for category, tickers in STOCK_CATEGORIES.items():
        result[category] = []
        for ticker in tickers:
            try:
                url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
                with urllib.request.urlopen(url, timeout=5) as response:
                    data = json.loads(response.read().decode())
                
                price = data.get('c', 0)
                change = data.get('dp', 0)
                
                if price and price > 0:
                    result[category].append({
                        'ticker': ticker,
                        'price': price,
                        'change': change
                    })
            except Exception:
                result[category].append({'ticker': ticker, 'error': True})
    
    return result

@st.cache_data(ttl=1800)
def fetch_news():
    """Fetch news from RSS feeds"""
    news_data = {'general': [], 'tech': [], 'market': []}
    
    for category, feeds in RSS_FEEDS.items():
        for feed_url, source_name in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:8]:
                    news_data[category].append({
                        'title': entry.get('title', 'No title'),
                        'link': entry.get('link', '#'),
                        'source': source_name
                    })
            except Exception:
                continue
    
    return news_data

@st.cache_data(ttl=300)
def fetch_notion_tasks():
    """Fetch tasks from Notion"""
    if not NOTION_API_KEY:
        return {'error': 'NOTION_API_KEY not configured'}
    
    try:
        url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
        
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        payload = {
            "filter": {
                "or": [
                    {"property": "Due", "date": {"on_or_before": today}},
                ]
            },
            "sorts": [{"property": "Due", "direction": "ascending"}]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code != 200:
            response = requests.post(url, headers=headers, json={}, timeout=10)
        
        data = response.json()
        tasks = data.get('results', [])
        
        # Filter out completed
        filtered = []
        for task in tasks:
            if not task:
                continue
            props = task.get('properties', {})
            is_done = False
            
            for prop_value in props.values():
                if prop_value is None or not isinstance(prop_value, dict):
                    continue
                prop_type = prop_value.get('type') or ''
                if prop_type == 'status':
                    status_info = prop_value.get('status') or {}
                    status_name = (status_info.get('name') or '').lower()
                    if 'done' in status_name or 'complete' in status_name:
                        is_done = True
                        break
            
            if not is_done:
                # Get title
                title = "Untitled"
                for prop_value in props.values():
                    if prop_value is None or not isinstance(prop_value, dict):
                        continue
                    if (prop_value.get('type') or '') == 'title':
                        titles = prop_value.get('title') or []
                        if titles:
                            title = (titles[0] or {}).get('plain_text', 'Untitled')
                        break
                
                # Get due date
                due = None
                for prop_value in props.values():
                    if prop_value is None or not isinstance(prop_value, dict):
                        continue
                    if (prop_value.get('type') or '') == 'due':
                        due_date = prop_value.get('date')
                        if due_date:
                            due = due_date.get('start')
                        break
                
                filtered.append({'title': title, 'due': due})
        
        return {'tasks': filtered[:15]}
    
    except Exception as e:
        return {'error': str(e)}

@st.cache_data(ttl=300)
def fetch_todoist_tasks():
    """Fetch tasks from Todoist"""
    if not TODOIST_API_KEY:
        return {'error': 'TODOIST_API_KEY not configured'}
    
    try:
        url = "https://api.todoist.com/rest/v2/tasks"
        
        headers = {
            "Authorization": f"Bearer {TODOIST_API_KEY}"
        }
        
        params = {"filter": "today | overdue", "limit": 20}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            tasks = response.json()
            return {'tasks': [{'title': t.get('content', 'Untitled'), 'due': t.get('due', {}).get('date')} for t in tasks]}
        else:
            return {'error': f'API error: {response.status_code}'}
    
    except Exception as e:
        return {'error': str(e)}

@st.cache_data(ttl=60)
def fetch_kimi_todos():
    """Parse Kimi's TODOs from markdown file"""
    try:
        if not Path(KIMI_TODOS_FILE).exists():
            return {'active': [], 'completed': []}
        
        with open(KIMI_TODOS_FILE, 'r') as f:
            content = f.read()
        
        active = []
        completed = []
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line == '## Active':
                current_section = 'active'
            elif line == '## Completed':
                current_section = 'completed'
            elif line.startswith('- [ ]') and current_section == 'active':
                active.append(line[5:].strip())
            elif line.startswith('- [x]') and current_section == 'completed':
                completed.append(line[6:].strip())
        
        return {'active': active, 'completed': completed}
    
    except Exception as e:
        return {'error': str(e)}

def get_mood_data():
    """Load mood data from JSON file"""
    try:
        if Path(MOOD_DATA_FILE).exists():
            with open(MOOD_DATA_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

def save_mood(mood, note=""):
    """Save mood entry to JSON file"""
    try:
        data = get_mood_data()
        today = datetime.now().strftime('%Y-%m-%d')
        
        if today not in data:
            data[today] = []
        
        data[today].append({
            'mood': mood,
            'note': note,
            'timestamp': datetime.now().isoformat()
        })
        
        with open(MOOD_DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Clear cache
        get_mood_data.clear()
        return True
    except Exception as e:
        return False

def get_decisions():
    """Load decisions from JSON file"""
    try:
        if Path(DECISIONS_FILE).exists():
            with open(DECISIONS_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception:
        return []

def add_decision(decision, context=""):
    """Add a decision to JSON file"""
    try:
        decisions = get_decisions()
        decisions.append({
            'timestamp': datetime.now().isoformat(),
            'decision': decision,
            'context': context
        })
        with open(DECISIONS_FILE, 'w') as f:
            json.dump(decisions, f, indent=2)
        return True
    except Exception:
        return False

def get_ideas():
    """Load ideas from JSON file"""
    try:
        if Path(IDEAS_FILE).exists():
            with open(IDEAS_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception:
        return []

def add_idea(idea, context=""):
    """Add an idea to JSON file"""
    try:
        ideas = get_ideas()
        ideas.append({
            'timestamp': datetime.now().isoformat(),
            'idea': idea,
            'context': context
        })
        with open(IDEAS_FILE, 'w') as f:
            json.dump(ideas, f, indent=2)
        return True
    except Exception:
        return False

@st.cache_data(ttl=300)
def get_aa_meetings():
    """Load AA meetings from JSON file"""
    try:
        if Path(AA_MEETINGS_FILE).exists():
            with open(AA_MEETINGS_FILE, 'r') as f:
                return json.load(f)
        return {'meetings': []}
    except Exception:
        return {'meetings': []}

def get_aa_attended():
    """Load AA attendance from JSON file"""
    try:
        if Path(AA_ATTENDED_FILE).exists():
            with open(AA_ATTENDED_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception:
        return []

def save_aa_attended(date_key, meeting_info):
    """Save AA attendance"""
    try:
        attended = get_aa_attended()
        
        # Remove existing entry for this date if exists
        attended = [a for a in attended if a.get('date') != date_key]
        
        attended.append({
            'date': date_key,
            'meeting': meeting_info,
            'timestamp': datetime.now().isoformat()
        })
        
        with open(AA_ATTENDED_FILE, 'w') as f:
            json.dump(attended, f, indent=2)
        
        return True
    except Exception:
        return False

@st.cache_data(ttl=300)
def get_activity_data():
    """Get activity data from sessions for heatmap"""
    try:
        sessions_path = Path(SESSIONS_DIR)
        if not sessions_path.exists():
            return []
        
        # Get recent session files
        sessions = []
        for f in sessions_path.glob("*.jsonl"):
            if '.deleted.' not in f.name and '.reset.' not in f.name:
                # Get modification time
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime > datetime.now() - timedelta(days=30):
                    # Count lines (messages)
                    try:
                        with open(f, 'r') as file:
                            lines = file.readlines()
                            sessions.append({
                                'date': mtime.date(),
                                'messages': len(lines)
                            })
                    except:
                        pass
        
        return sessions
    except Exception:
        return []

# ============================================================================
# MAIN APP
# ============================================================================

# Navigation
pages = [
    "🏠 Dashboard",
    "📰 News",
    "📈 Stocks",
    "😊 Mood",
    "📝 Decisions",
    "💡 Ideas",
    "✅ Tasks",
    "🔥 Activity"
]

st.title("🎯 Life Dashboard")

# Top navigation
page = st.radio(
    "Navigate",
    pages + ["🔒 Logout"],
    horizontal=True,
    label_visibility="collapsed"
)

# Handle logout
if page == "🔒 Logout":
    st.session_state.authenticated = False
    st.rerun()

# ==================== DASHBOARD ====================
if page == "🏠 Dashboard":
    st.header("🏠 Dashboard")
    
    # Weather
    st.subheader("🌤️ Weather")
    try:
        weather = fetch_weather()
        if 'error' not in weather.get('current', {}):
            current = weather['current']
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Temperature", f"{current['temp']}°F")
            with col2:
                st.metric("Feels Like", f"{current['feels_like']}°F")
            with col3:
                st.metric("Humidity", f"{current['humidity']}%")
            with col4:
                st.metric("Wind", f"{current['wind']} mph")
            
            # Forecast
            if weather['forecast']:
                cols = st.columns(7)
                for i, day in enumerate(weather['forecast']):
                    with cols[i]:
                        st.markdown(f"**{day['day']}**")
                        st.markdown(f"{day['icon']}")
                        st.caption(f"{day['high']}° / {day['low']}°")
        else:
            st.error(f"Weather unavailable: {weather['current'].get('error')}")
    except Exception as e:
        st.error(f"Weather error: {e}")
    
    st.markdown("---")
    
    # Sobriety Counter
    st.subheader("🍀 Sobriety Counter")
    sobriety = get_sobriety_counter()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Days Sober", f"{sobriety['days']}")
    with col2:
        st.caption(sobriety['duration'])
    
    st.markdown(f"> *\"{sobriety['quote']}\"*  \n> — {sobriety['author']}")
    
    st.markdown("---")
    
    # System Info
    st.subheader("💻 System Info")
    try:
        sys_info = get_system_info()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("CPU", f"{sys_info['cpu']}%")
            st.progress(sys_info['cpu'] / 100)
        with col2:
            st.metric("RAM", f"{sys_info['ram']}%")
            st.progress(sys_info['ram'] / 100)
        with col3:
            st.metric("Disk", f"{sys_info['disk']}%")
            st.progress(sys_info['disk'] / 100)
    except Exception as e:
        st.error(f"System info error: {e}")

# ==================== NEWS ====================
elif page == "📰 News":
    st.header("📰 News")
    
    news_tab = st.tabs(["General", "Tech+AI", "Market"])
    
    try:
        news = fetch_news()
    except Exception as e:
        st.error(f"Error fetching news: {e}")
        news = {'general': [], 'tech': [], 'market': []}
    
    with news_tab[0]:
        st.subheader("General News")
        if news['general']:
            for item in news['general'][:15]:
                st.markdown(f"- [{item['title']}]({item['link']})  \n  *{item['source']}*")
        else:
            st.info("No news available")
    
    with news_tab[1]:
        st.subheader("Tech & AI News")
        if news['tech']:
            for item in news['tech'][:15]:
                st.markdown(f"- [{item['title']}]({item['link']})  \n  *{item['source']}*")
        else:
            st.info("No news available")
    
    with news_tab[2]:
        st.subheader("Market News")
        if news['market']:
            for item in news['market'][:15]:
                st.markdown(f"- [{item['title']}]({item['link']})  \n  *{item['source']}*")
        else:
            st.info("No news available")

# ==================== STOCKS ====================
elif page == "📈 Stocks":
    st.header("📈 Stock Quotes")
    
    try:
        stocks = fetch_stocks()
        
        if 'error' in stocks:
            st.error(stocks['error'])
        else:
            for category, tickers in stocks.items():
                st.subheader(f"**{category}**")
                
                cols = st.columns(len(tickers) if tickers else 1)
                for i, stock in enumerate(tickers):
                    with cols[i] if i < len(cols) else cols[0]:
                        if 'error' in stock:
                            st.metric(stock['ticker'], "—")
                        else:
                            delta = stock['change'] if stock['change'] else 0
                            st.metric(stock['ticker'], f"${stock['price']:.2f}", f"{delta:+.2f}%")
                
                st.markdown("")
    
    except Exception as e:
        st.error(f"Error fetching stocks: {e}")

# ==================== MOOD ====================
elif page == "😊 Mood":
    st.header("😊 Mood Tracker")
    
    # Mood input
    moods = {
        "😢": "awful",
        "😔": "bad",
        "😐": "okay",
        "🙂": "good",
        "😊": "great",
        "🤩": "amazing"
    }
    
    st.subheader("How are you feeling?")
    
    cols = st.columns(len(moods))
    selected_mood = None
    
    for i, (emoji, mood_name) in enumerate(moods.items()):
        with cols[i]:
            if st.button(emoji, key=f"mood_{mood_name}"):
                selected_mood = mood_name
    
    if selected_mood:
        note = st.text_input("Add a note (optional)", key="mood_note")
        if st.button("Save Mood", key="save_mood"):
            if save_mood(selected_mood, note):
                st.success(f"Mood saved: {selected_mood}!")
                st.rerun()
            else:
                st.error("Failed to save mood")
    
    st.markdown("---")
    
    # Mood history
    st.subheader("📊 Mood History")
    
    try:
        mood_data = get_mood_data()
        
        if mood_data:
            # Flatten mood data
            all_moods = []
            mood_values = {"awful": 1, "bad": 2, "okay": 3, "good": 4, "great": 5, "amazing": 6}
            
            for date_str, entries in sorted(mood_data.items(), reverse=True)[:14]:
                for entry in entries:
                    all_moods.append({
                        'date': date_str,
                        'mood': entry.get('mood', 'okay'),
                        'note': entry.get('note', ''),
                        'timestamp': entry.get('timestamp', ''),
                        'value': mood_values.get(entry.get('mood', 'okay'), 3)
                    })
            
            if all_moods:
                # Show recent moods
                st.write("Recent entries:")
                for item in all_moods[:10]:
                    emoji = [e for e, m in moods.items() if m == item['mood']][0] if item['mood'] in moods.values() else "😐"
                    st.write(f"{emoji} **{item['date']}**: {item['mood']} - {item['note']}")
                
                # Simple bar chart
                df = pd.DataFrame(all_moods[:30])
                if not df.empty and 'date' in df.columns:
                    chart = alt.Chart(df).mark_bar().encode(
                        x='date',
                        y=alt.Y('value', title='Mood'),
                        color=alt.Color('mood')
                    ).properties(height=200)
                    st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No mood entries yet")
        else:
            st.info("No mood data yet. Add your first mood above!")
    
    except Exception as e:
        st.error(f"Error loading mood data: {e}")

# ==================== DECISIONS ====================
elif page == "📝 Decisions":
    st.header("📝 Decision Log")
    
    # Add new decision
    with st.expander("➕ Add New Decision", expanded=False):
        new_decision = st.text_input("What did you decide?", key="new_decision")
        context = st.text_input("Context (optional)", key="decision_context")
        if st.button("Save Decision"):
            if new_decision:
                if add_decision(new_decision, context):
                    st.success("Decision saved!")
                    st.rerun()
                else:
                    st.error("Failed to save decision")
            else:
                st.warning("Please enter a decision")
    
    st.markdown("---")
    
    # View decisions
    try:
        decisions = get_decisions()
        
        if decisions:
            # Sort by timestamp
            decisions = sorted(decisions, key=lambda x: x.get('timestamp', ''), reverse=True)
            
            for d in decisions:
                ts = d.get('timestamp', '')
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    date_str = ts
                
                with st.expander(f"📝 {date_str}"):
                    st.markdown(f"**Decision:** {d.get('decision', '')}")
                    if d.get('context'):
                        st.caption(f"Context: {d.get('context', '')}")
        else:
            st.info("No decisions logged yet.")
    
    except Exception as e:
        st.error(f"Error loading decisions: {e}")

# ==================== IDEAS ====================
elif page == "💡 Ideas":
    st.header("💡 Ideas Vault")
    
    # Add new idea
    with st.expander("➕ Add New Idea", expanded=False):
        new_idea = st.text_input("What's your idea?", key="new_idea")
        context = st.text_input("Context (optional)", key="idea_context")
        if st.button("Save Idea"):
            if new_idea:
                if add_idea(new_idea, context):
                    st.success("Idea saved!")
                    st.rerun()
                else:
                    st.error("Failed to save idea")
            else:
                st.warning("Please enter an idea")
    
    st.markdown("---")
    
    # View ideas
    try:
        ideas = get_ideas()
        
        if ideas:
            # Sort by timestamp
            ideas = sorted(ideas, key=lambda x: x.get('timestamp', ''), reverse=True)
            
            for i in ideas:
                ts = i.get('timestamp', '')
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    date_str = ts
                
                with st.expander(f"💡 {date_str}"):
                    st.markdown(f"**Idea:** {i.get('idea', '')}")
                    if i.get('context'):
                        st.caption(f"Context: {i.get('context', '')}")
        else:
            st.info("No ideas yet.")
    
    except Exception as e:
        st.error(f"Error loading ideas: {e}")

# ==================== TASKS ====================
elif page == "✅ Tasks":
    st.header("✅ Tasks")
    
    # Tabs for different task sources
    task_tabs = st.tabs(["Notion", "Todoist", "Kimi's TODOs"])
    
    with task_tabs[0]:
        st.subheader("📓 Notion Tasks")
        try:
            notion = fetch_notion_tasks()
            if 'error' in notion:
                st.warning(notion['error'])
            elif notion.get('tasks'):
                for task in notion['tasks']:
                    due_str = f" (due: {task['due']})" if task.get('due') else ""
                    st.markdown(f"- [ ] {task['title']}{due_str}")
            else:
                st.success("🎉 No pending Notion tasks!")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with task_tabs[1]:
        st.subheader("✅ Todoist Tasks")
        try:
            todoist = fetch_todoist_tasks()
            if 'error' in todoist:
                st.warning(todoist['error'])
            elif todoist.get('tasks'):
                for task in todoist['tasks']:
                    due_str = f" (due: {task['due']})" if task.get('due') else ""
                    st.markdown(f"- [ ] {task['title']}{due_str}")
            else:
                st.success("🎉 No pending Todoist tasks!")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with task_tabs[2]:
        st.subheader("🐶 Kimi's TODOs")
        try:
            kimi = fetch_kimi_todos()
            if 'error' in kimi:
                st.warning(kimi['error'])
            else:
                if kimi.get('active'):
                    st.markdown("**Active:**")
                    for todo in kimi['active']:
                        st.markdown(f"- [ ] {todo}")
                else:
                    st.info("No active tasks")
                
                if kimi.get('completed'):
                    with st.expander("Completed"):
                        for todo in kimi['completed']:
                            st.markdown(f"- [x] {todo}")
        except Exception as e:
            st.error(f"Error: {e}")

# ==================== ACTIVITY ====================
elif page == "🔥 Activity":
    st.header("🔥 Activity Heatmap")
    
    try:
        sessions = get_activity_data()
        
        if sessions:
            # Aggregate by date
            date_counts = defaultdict(int)
            for s in sessions:
                date_counts[s['date']] += s['messages']
            
            # Create dataframe
            data = []
            for d, count in sorted(date_counts.items()):
                data.append({'date': d.isoformat(), 'messages': count})
            
            df = pd.DataFrame(data)
            
            if not df.empty:
                # Simple heatmap using Altair
                df['date'] = pd.to_datetime(df['date'])
                df['day'] = df['date'].dt.dayofweek
                df['week'] = df['date'].dt.isocalendar().week
                df['month'] = df['date'].dt.month_name()
                
                # Chart
                chart = alt.Chart(df).mark_rect().encode(
                    x=alt.X('date', title='Date'),
                    y=alt.Y('messages', title='Messages'),
                    color=alt.Color('messages', scale=alt.Scale(scheme='greens'))
                ).properties(height=300)
                
                st.altair_chart(chart, use_container_width=True)
                
                # Stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Sessions", len(data))
                with col2:
                    st.metric("Total Messages", df['messages'].sum())
                with col3:
                    st.metric("Avg Messages/Day", f"{df['messages'].mean():.1f}")
            else:
                st.info("No activity data available")
        else:
            st.info("No recent session data available")
    
    except Exception as e:
        st.error(f"Error loading activity data: {e}")

# Footer
st.markdown("---")
st.caption(f"🎯 Life Dashboard | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
