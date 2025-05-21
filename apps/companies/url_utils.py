from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class URLValidator:
    def __init__(self, main_info: Dict[str, str]):
        self.main_info = main_info
        self.company_name = main_info.get('name', '').lower()
        self.company_description = main_info.get('description', '').lower()
        self.industry = main_info.get('industry', '').lower()

    def is_valid_company_url(self, url: str) -> bool:
        """Validate if URL is related to the company based on main information"""
        try:
            # Parse URL
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check if domain contains company name
            if self.company_name in domain:
                return True

            # Check if URL is from known company domains
            known_domains = [
                'linkedin.com/company',
                'crunchbase.com/organization',
                'bloomberg.com/profile/company',
                'reuters.com/companies',
                'wsj.com/market-data/quotes'
            ]

            return any(known_domain in domain for known_domain in known_domains)

        except Exception as e:
            logger.error(f"Error validating URL {url}: {str(e)}")
            return False


class URLCrawler:
    def __init__(self, max_depth: int = 2, max_urls_per_page: int = 10):
        self.max_depth = max_depth
        self.max_urls_per_page = max_urls_per_page
        self.visited_urls: Set[str] = set()

    def extract_urls(self, url: str) -> List[str]:
        """Extract URLs from a webpage"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            base_url = response.url

            # Extract all links
            urls = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(base_url, href)

                # Only include http(s) URLs
                if absolute_url.startswith(('http://', 'https://')):
                    urls.append(absolute_url)

            return urls[:self.max_urls_per_page]

        except Exception as e:
            logger.error(f"Error extracting URLs from {url}: {str(e)}")
            return []

    def crawl(self, start_url: str) -> List[str]:
        """Crawl URLs up to specified depth"""
        self.visited_urls.clear()
        urls_to_visit = [(start_url, 0)]  # (url, depth)
        all_urls = []

        while urls_to_visit:
            current_url, depth = urls_to_visit.pop(0)

            if current_url in self.visited_urls or depth > self.max_depth:
                continue

            self.visited_urls.add(current_url)
            all_urls.append(current_url)

            if depth < self.max_depth:
                new_urls = self.extract_urls(current_url)
                urls_to_visit.extend([(url, depth + 1) for url in new_urls])

        return all_urls


class BusinessQueryGenerator:
    def __init__(self, company_name: str):
        self.company_name = company_name

    def generate_queries(self) -> List[str]:
        """Generate business analysis queries"""
        return [
            f"{self.company_name} Revenue Metrics Q4 2024",
            f"{self.company_name} Team Management",
            f"{self.company_name} Investments Portfolio 2023",
            f"{self.company_name} Financial Performance",
            f"{self.company_name} Business Strategy",
            f"{self.company_name} Market Position",
            f"{self.company_name} Competitors Analysis",
            f"{self.company_name} Growth Strategy",
            f"{self.company_name} Recent Acquisitions",
            f"{self.company_name} Future Plans"
        ]


def extract_main_info(url: str) -> Dict[str, str]:
    """Extract main company information from a webpage"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract title
        title = soup.title.string if soup.title else ''

        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc['content'] if meta_desc else ''

        # Extract company name from title or first h1
        h1 = soup.find('h1')
        company_name = h1.string if h1 else title.split('|')[0].strip()

        return {
            'name': company_name,
            'description': description,
            'title': title
        }

    except Exception as e:
        logger.error(f"Error extracting main info from {url}: {str(e)}")
        return {} 