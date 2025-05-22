import json
import os
from pydantic import BaseModel
from core.prompt_manager import PromptManager, get_tavily_response
from .prompts import QUERY_GENERATOR_PROMPT, BUSINESS_PROFILE_PROMPT, FINANCIAL_COMPARISON_PROMPT, \
    COMPANY_QUERIES_PROMPT, COMPANIES_COMPARISON_PROMPT, DOCUMENT_ANALYSIS_PROMPT, INVESTMENT_SCORING_PROMPT
from .utils import tavily_client
from openai import OpenAI
from tavily import TavilyClient
from dotenv import load_dotenv
from core.methods import send_notification
from .url_utils import URLValidator, URLCrawler, BusinessQueryGenerator, extract_main_info
import requests
import logging

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

logger = logging.getLogger(__name__)


class Queries(BaseModel):
    category: str
    queries: list[str]


class ComparisonResult(BaseModel):
    winner_company: str
    superiority_percentage: int
    comparison_details: str


def generate_query(topic, company_name):
    prompt = COMPANY_QUERIES_PROMPT.format(topic=topic, company_name=company_name)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    return json.loads(response.choices[0].message.content)


def research(query: str) -> str:
    """Enhanced research function with deep crawling and validation"""
    try:
        # Initialize components
        prompt_manager = PromptManager()
        url_crawler = URLCrawler(max_depth=2)

        # Get initial company info from Tavily
        tavily_response = get_tavily_response(query)
        if not tavily_response:
            print('NO RESPONSE')
            return "No results found from Tavily search."

        # Process tavily_response based on its structure
        print('TAVILY RESPONSE RECEIVED')
        
        main_info = {}
        valid_urls = []
        
        if isinstance(tavily_response, dict):
            # Handle error responses
            if 'error' in tavily_response:
                return f"Error from Tavily search: {tavily_response['error']}"
            
            # Extract main company info
            if 'main_company_info' in tavily_response:
                main_info = tavily_response['main_company_info']
                
            # Extract valid URLs
            if 'valid_urls' in tavily_response and tavily_response['valid_urls']:
                valid_urls = tavily_response['valid_urls']
                
                # Extract main URL from valid URLs
                main_url = None
                for url in valid_urls:
                    if 'linkedin.com' not in url.lower() and 'twitter.com' not in url.lower() and 'facebook.com' not in url.lower():
                        main_url = url
                        break
                
                if not main_url and valid_urls:
                    main_url = valid_urls[0]
                    
                # If we have a main URL, extract additional info from it
                if main_url:
                    additional_info = extract_main_info(main_url)
                    if additional_info:
                        # Merge additional info with main_info
                        for key, value in additional_info.items():
                            if key not in main_info or not main_info[key]:
                                main_info[key] = value
            
            # Add company name to main_info if not present
            if 'name' not in main_info or not main_info['name']:
                main_info['name'] = query
                
            # Extract data from business_analysis if available
            business_analysis = tavily_response.get('business_analysis', {})
            
            # Add industry from business_analysis if not in main_info
            if business_analysis and ('industry' not in main_info or not main_info.get('industry')):
                # Try to extract industry from business_analysis
                text = str(business_analysis)
                lower_text = text.lower()
                
                # Check for industry mentions
                industry_indicators = [
                    "industry", "sector", "field", "market"
                ]
                
                for indicator in industry_indicators:
                    if indicator in lower_text:
                        # Find the sentence containing this indicator
                        idx = lower_text.find(indicator)
                        start = max(0, lower_text.rfind('.', 0, idx) + 1)
                        end = lower_text.find('.', idx)
                        if end == -1:
                            end = len(lower_text)
                        
                        industry_sentence = text[start:end].strip()
                        # Add to main_info
                        main_info['industry'] = industry_sentence
                        break
        else:
            # Invalid response format
            return "Invalid response format from Tavily search."
            
        # Generate additional business queries
        if 'name' in main_info:
            query_generator = BusinessQueryGenerator(main_info['name'])
        else:
            query_generator = BusinessQueryGenerator(query)
            
        business_queries = query_generator.generate_queries()

        # Search for each business query
        all_results = []
        for business_query in business_queries:
            search_results = get_tavily_response(business_query)
            if search_results:
                all_results.append(search_results)
                
                # Try to extract additional info from these results
                if isinstance(search_results, dict) and 'main_company_info' in search_results:
                    for key, value in search_results['main_company_info'].items():
                        if key not in main_info or not main_info[key]:
                            main_info[key] = value

        # Aggregate results
        context = f"Main Company Information:\n{json.dumps(main_info, indent=2)}\n\n"
        context += f"Valid URLs Found:\n{json.dumps(valid_urls, indent=2)}\n\n"
        context += f"Business Analysis Results:\n{json.dumps(all_results, indent=2)}"

        return context

    except Exception as e:
        logger.error(f"Error in research: {str(e)}")
        return f"Error during research: {str(e)}"


def generate_business_profile(context, company_name=None):
    """
    Generate business profile based on context and company name.
    If company_name is not provided, try to extract it from the context.
    """
    # Try to extract company name from context if not provided
    if company_name is None:
        # Simple extraction - look for the company name in the first few queries
        lines = context.split('\n')
        for line in lines[:10]:
            if line.startswith("Query:"):
                query_parts = line.replace("Query:", "").strip().split()
                # Assume first term that's not a common word is the company name
                for part in query_parts:
                    if len(part) > 2 and part.lower() not in ['the', 'and', 'for', 'of', 'in', 'on', 'at', 'to', 'a',
                                                              'an']:
                        company_name = part
                        break
                if company_name:
                    break

        # Fallback
        if not company_name:
            company_name = "The Company"

    prompt = BUSINESS_PROFILE_PROMPT.format(company_name=company_name, context=context)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


def compare_company_finances(company_profiles, company_names):
    """Compare multiple company profiles and determine investment insights"""

    prompt = COMPANIES_COMPARISON_PROMPT.format(
        company_profiles=json.dumps(company_profiles),
        company_names=json.dumps(company_names)
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


def analyze_document(document_text, company_name):
    """Extract key points from document text"""

    prompt = DOCUMENT_ANALYSIS_PROMPT.format(
        document_text=document_text[:10000],  # Truncate if too long
        company_name=company_name
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


def calculate_investment_scores(company_profile):
    """Calculate investment scores based on company profile"""

    prompt = INVESTMENT_SCORING_PROMPT.format(company_profile=company_profile)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    return json.loads(response.choices[0].message.content)