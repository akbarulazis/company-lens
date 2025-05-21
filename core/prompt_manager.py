from openai import OpenAI
from pydantic import BaseModel
from typing import Dict, List, Optional
import os

# Initialize OpenAI client
openai_client = OpenAI()

# Tavily API key (you should store this securely)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY environment variable not set.")


class PromptManager:
    def __init__(self, model="gpt-4o", messages=[]):
        self.model = model
        self.messages = messages

    def add_message(self, role, message):
        self.messages.append({"role": role, "content": message})

    def add_messages(self, messages):
        self.messages.extend(messages)

    def generate(self):
        response = openai_client.chat.completions.create(
            model=self.model,
            messages=self.messages
        )

        content = response.choices[0].message.content
        return content

    def generate_structured(self, schema: BaseModel):
        response = openai_client.beta.chat.completions.parse(
            model=self.model,
            messages=self.messages,
            response_format=schema
        )

        content = response.choices[0].message.parsed
        data = schema.model_dump(content)
        return data

# Define Pydantic schema for structured output
class CompanyResponse(BaseModel):
    main_company_info: dict
    valid_urls: list[str]
    business_analysis: dict


def get_tavily_response(query: str) -> dict:
    """
    Fetches search results from Tavily and returns structured company data using PromptManager.
    """

    # Step 1: Get search results from Tavily
    from tavily import TavilyClient
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(query=query, max_results=3)
    if not response:
        return {"error": "No results found from Tavily search."}

    # Step 2: Create prompt based on Tavily results
    search_results_str = "\n".join([f"Title: {item['title']}\nURL: {item['url']}\nSnippet: {item['snippet']}" for item in response])

    prompt = f"""
    You are an AI assistant. Based on the following search results, extract the following information:

    1. Main Company Information:
       - Name
       - Description
       - Location
       - Website URL

    2. Valid URLs Found:
       - List all relevant URLs from the search results.

    3. Business Analysis Results:
       - Provide a brief analysis of the company's industry, market position, and key products.

    Search Results:
    {search_results_str}
    """

    # Step 3: Use PromptManager to generate structured response
    prompt_manager = PromptManager(model="gpt-4o")
    prompt_manager.add_message("user", prompt)

    try:
        result = prompt_manager.generate_structured(schema=CompanyResponse)
        return result
    except Exception as e:
        return {"error": f"Failed to generate structured response: {str(e)}"}