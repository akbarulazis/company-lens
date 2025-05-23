from tavily import TavilyClient
from dotenv import load_dotenv
import os
import uuid
import markdown
from bs4 import BeautifulSoup
import re

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


def generate_id():
    """Generate a short unique ID"""
    return uuid.uuid4().hex[:24]


def markdown_to_html(content):
    """Convert markdown text to clean HTML"""
    if not content:
        return ""

    # Pre-process content to handle common issues
    # Replace extra ** that might not be properly paired
    content = re.sub(r'\*\*\s', '** ', content)  # Fix cases where ** is followed by space
    content = re.sub(r'\s\*\*', ' **', content)  # Fix cases where ** is preceded by space

    # Make sure all # headers have a space after them
    content = re.sub(r'#([^#\s])', r'# \1', content)
    content = re.sub(r'##([^#\s])', r'## \1', content)
    content = re.sub(r'###([^#\s])', r'### \1', content)

    # Convert markdown to HTML
    html = markdown.markdown(content, extensions=['tables', 'fenced_code'])

    # Clean and improve formatting
    soup = BeautifulSoup(html, 'html.parser')

    # Add Bootstrap classes to elements
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        heading['class'] = heading.get('class', []) + ['mt-4', 'mb-3']

    for ul in soup.find_all('ul'):
        ul['class'] = ul.get('class', []) + ['list-group', 'list-group-flush', 'mb-4']

    for li in soup.find_all('li'):
        li['class'] = li.get('class', []) + ['list-group-item', 'border-0', 'ps-0']

    for p in soup.find_all('p'):
        p['class'] = p.get('class', []) + ['mb-3']

    # Format horizontal rules
    for hr in soup.find_all('hr'):
        hr['class'] = hr.get('class', []) + ['my-4']

    # Format tables nicely
    for table in soup.find_all('table'):
        table['class'] = table.get('class', []) + ['table', 'table-striped', 'table-bordered']

    return str(soup)
