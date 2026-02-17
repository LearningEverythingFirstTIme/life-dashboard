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

# Get API keys - first try Streamlit secrets, then environment variables
# Streamlit Cloud secrets are accessed via st.secrets
try:
    NOTION_API_KEY = st.secrets.get('NOTION_API_KEY', os.environ.get('NOTION_API_KEY', ''))
except:
    NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')

try:
    NOTION_DATABASE_ID = st.secrets.get('NOTION_DATABASE_ID', os.environ.get('NOTION_DATABASE_ID', '287cb484-7040-45cd-a44b-315dddbcd010'))
except:
    NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '287cb484-7040-45cd-a44b-315dddbcd010')

try:
    TODOIST_API_KEY = st.secrets.get('TODOIST_API_KEY', os.environ.get('TODOIST_API_KEY', ''))
except:
    TODOIST_API_KEY = os.environ.get('TODOIST_API_KEY', '')

try:
    FINNHUB_API_KEY = st.secrets.get('FINNHUB_API_KEY', os.environ.get('FINNHUB_API_KEY', ''))
except:
    FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', '')

# File paths (relative for Streamlit Cloud)
MOOD_DATA_FILE = "mood_data.json"
DECISIONS_FILE = "decisions.json"
IDEAS_FILE = "ideas.json"
AA_MEETINGS_FILE = "aa_meetings.json"
AA_ATTENDED_FILE = "aa_attended.json"
KIMI_TODOS_FILE = "kimi_todos.md"
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
    """Fetch stock quotes from Finnhub with proper error handling"""
    if not FINNHUB_API_KEY:
        return {'error': 'Configure FINNHUB_API_KEY in Streamlit Cloud secrets'}
    
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
                else:
                    result[category].append({'ticker': ticker, 'error': True})
            except Exception:
                result[category].append({'ticker': ticker, 'error': True})
    
    return result

@st.cache_data(ttl=1800)
def fetch_news():
    """Fetch news from RSS feeds with proper error handling"""
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
    """Fetch tasks from Notion with proper error handling"""
    if not NOTION_API_KEY:
        return {'error': 'Configure NOTION_API_KEY in Streamlit Cloud secrets'}
    
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
        return {'error': f'Configure NOTION_API_KEY in Streamlit Cloud secrets: {str(e)}'}

@st.cache_data(ttl=300)
def fetch_todoist_tasks():
    """Fetch tasks from Todoist with proper error handling"""
    if not TODOIST_API_KEY:
        return {'error': 'Configure TODOIST_API_KEY in Streamlit Cloud secrets'}
    
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
            return {'error': f'Configure TODOIST_API_KEY in Streamlit Cloud secrets'}
    
    except Exception as e:
        return {'error': f'Configure TODOIST_API_KEY in Streamlit Cloud secrets'}

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
# MAIN APP - SINGLE PAGE LAYOUT
# ============================================================================

st.title("🎯 Life Dashboard")

# Row 1: Weather | Sobriety Counter (2 columns)
st.subheader("📊 Today's Overview")
row1_col1, row1_col2 = st.columns(2)

# Weather (Column 1)
with row1_col1:
    st.markdown("### 🌤️ Weather")
    try:
        weather = fetch_weather()
        if 'error' not in weather.get('current', {}):
            current = weather['current']
            st.metric("Temperature", f"{current['temp']}°F")
            st.caption(f"{current['icon']} {current['condition']}")
            st.caption(f"Feels like: {current['feels_like']}°F | Humidity: {current['humidity']}% | Wind: {current['wind']} mph")
            
            # Small forecast
            if weather['forecast']:
                forecast_cols = st.columns(7)
                for i, day in enumerate(weather['forecast']):
                    with forecast_cols[i]:
                        st.caption(f"**{day['day']}**")
                        st.caption(f"{day['icon']}")
                        st.caption(f"{day['high']}°/{day['low']}°")
        else:
            st.warning(f"Weather unavailable")
    except Exception as e:
        st.warning(f"Weather unavailable")

# Sobriety Counter (Column 2)
with row1_col2:
    st.markdown("### 🍀 Sobriety Counter")
    sobriety = get_sobriety_counter()
    st.metric("Days Sober", f"{sobriety['days']}")
    st.caption(sobriety['duration'])
    st.markdown(f"> *\"{sobriety['quote']}\"*  \n> — {sobriety['author']}")

st.markdown("---")

# Row 1.5: AA Meetings
DAY_MAP = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
today_day = datetime.now().weekday()
day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

with st.expander("🍀 AA Meetings This Week", expanded=True):
    try:
        import json
        with open('aa_meetings.json', 'r') as f:
            meetings_data = json.load(f)
        
        meetings = meetings_data.get('meetings', [])
        
        # Show today's and upcoming meetings
        st.markdown("### 📅 This Week's Meetings")
        
        # Get this week's meetings starting from today
        week_meetings = []
        for i in range(7):
            check_day = (today_day + i) % 7
            day_name = day_names[check_day]
            day_meetings = [m for m in meetings if m.get('day', '').lower() == day_name.lower()]
            for m in day_meetings:
                week_meetings.append({
                    'day': day_name,
                    'time': m.get('time', ''),
                    'town': m.get('town', ''),
                    'type': ', '.join(m.get('type', [])),
                    'location': m.get('location', ''),
                    'distance': m.get('distance', 0),
                    'is_today': i == 0
                })
        
        if week_meetings:
            for m in week_meetings:
                day_indicator = "🟢 " if m['is_today'] else ""
                st.markdown(f"**{day_indicator}{m['day']} {m['time']}** — {m['town']} ({m['type']})")
                st.caption(f"📍 {m['location']}")
                if m['distance'] > 0:
                    st.caption(f"🚗 {m['distance']} miles")
                st.markdown("")
        else:
            st.info("No meetings found")
        
        # Attendance streak (placeholder)
        st.markdown("---")
        st.markdown("### 📊 Your Progress")
        st.metric("Attendance Streak", "🔥 3 weeks")
        
        # Quick "I attended" button
        if st.button("✅ I Attended Today!", key="i_attended"):
            st.success("Great job! Keep coming back! 🍀")
            
    except Exception as e:
        st.error(f"Error loading meetings: {e}")

# Row 2: News (expander with 3 tabs)
with st.expander("📰 News", expanded=False):
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
            st.info("No news available. Check RSS feed configuration.")
    
    with news_tab[1]:
        st.subheader("Tech & AI News")
        if news['tech']:
            for item in news['tech'][:15]:
                st.markdown(f"- [{item['title']}]({item['link']})  \n  *{item['source']}*")
        else:
            st.info("No news available. Check RSS feed configuration.")
    
    with news_tab[2]:
        st.subheader("Market News")
        if news['market']:
            for item in news['market'][:15]:
                st.markdown(f"- [{item['title']}]({item['link']})  \n  *{item['source']}*")
        else:
            st.info("No news available. Check RSS feed configuration.")

# Row 3: (removed Stocks - no API key configured)

# Row 4: (removed Mood - needs redesign)

# Row 5: Decisions + Ideas (two columns in expander)
with st.expander("📝 Decisions & 💡 Ideas", expanded=False):
    col_decisions, col_ideas = st.columns(2)
    
    # Decisions (Column 1)
    with col_decisions:
        st.markdown("### 📝 Decision Log")
        
        # Add new decision
        with st.expander("➕ Add New Decision", expanded=False):
            new_decision = st.text_input("What did you decide?", key="new_decision")
            context = st.text_input("Context (optional)", key="decision_context")
            if st.button("Save Decision", key="save_decision"):
                if new_decision:
                    if add_decision(new_decision, context):
                        st.success("Decision saved!")
                        st.rerun()
                    else:
                        st.error("Failed to save decision")
                else:
                    st.warning("Please enter a decision")
        
        # View decisions
        try:
            decisions = get_decisions()
            
            if decisions:
                # Sort by timestamp
                decisions = sorted(decisions, key=lambda x: x.get('timestamp', ''), reverse=True)
                
                for d in decisions[:10]:
                    ts = d.get('timestamp', '')
                    try:
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        date_str = ts
                    
                    st.markdown(f"**{date_str}**: {d.get('decision', '')}")
                    if d.get('context'):
                        st.caption(f"Context: {d.get('context', '')}")
            else:
                st.info("No decisions logged yet.")
        
        except Exception as e:
            st.error(f"Error loading decisions: {e}")
    
    # Ideas (Column 2)
    with col_ideas:
        st.markdown("### 💡 Ideas Vault")
        
        # Add new idea
        with st.expander("➕ Add New Idea", expanded=False):
            new_idea = st.text_input("What's your idea?", key="new_idea")
            idea_context = st.text_input("Context (optional)", key="idea_context")
            if st.button("Save Idea", key="save_idea"):
                if new_idea:
                    if add_idea(new_idea, idea_context):
                        st.success("Idea saved!")
                        st.rerun()
                    else:
                        st.error("Failed to save idea")
                else:
                    st.warning("Please enter an idea")
        
        # View ideas
        try:
            ideas = get_ideas()
            
            if ideas:
                # Sort by timestamp
                ideas = sorted(ideas, key=lambda x: x.get('timestamp', ''), reverse=True)
                
                for i in ideas[:10]:
                    ts = i.get('timestamp', '')
                    try:
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        date_str = ts
                    
                    st.markdown(f"**{date_str}**: {i.get('idea', '')}")
                    if i.get('context'):
                        st.caption(f"Context: {i.get('context', '')}")
            else:
                st.info("No ideas yet.")
        
        except Exception as e:
            st.error(f"Error loading ideas: {e}")

# Row 6: Tasks tabs (expander)
with st.expander("✅ Tasks", expanded=False):
    task_tabs = st.tabs(["Todoist", "Kimi's TODOs"])
    
    with task_tabs[0]:
        st.markdown("### ✅ Todoist Tasks")
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
    
    with task_tabs[1]:
        st.markdown("### 🐶 Kimi's TODOs")
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

# Row 7: Activity (expander)
with st.expander("🔥 Activity", expanded=False):
    st.markdown("### Activity Heatmap")
    
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

# Logout button
st.markdown("---")
if st.button("🔒 Logout"):
    st.session_state.authenticated = False
    st.rerun()

# Footer
st.caption(f"🎯 Life Dashboard | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
