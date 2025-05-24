import logging
import time
import os
from openai import OpenAI, APIError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)

# Initialize the OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def openai_with_retry(model="gpt-4o-mini", messages=None, temperature=0.7, max_tokens=None, 
                      max_retries=3, initial_retry_delay=1, functions=None, function_call=None):
    """
    Wrapper for OpenAI API calls with retry logic for rate limits and errors.
    
    Args:
        model (str): The OpenAI model to use
        messages (list): List of message objects for the conversation
        temperature (float): Temperature for response generation
        max_tokens (int, optional): Maximum tokens in the response
        max_retries (int): Maximum number of retries
        initial_retry_delay (int): Initial delay before retrying in seconds
        functions (list, optional): Function definitions for function calling
        function_call (dict, optional): Function call specification
    
    Returns:
        The OpenAI API response
    """
    messages = messages or []
    retry_count = 0
    retry_delay = initial_retry_delay
    
    while retry_count <= max_retries:
        try:
            # Prepare API call parameters
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
                
            if functions:
                params["functions"] = functions
                
            if function_call:
                params["function_call"] = function_call
            
            # Make the API call
            return client.chat.completions.create(**params)
            
        except RateLimitError:
            if retry_count == max_retries:
                logger.error(f"Rate limit exceeded after {max_retries} retries. Giving up.")
                raise
            
            logger.warning(f"Rate limit exceeded. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
            retry_count += 1
            
        except (APIError, APITimeoutError) as e:
            if retry_count == max_retries:
                logger.error(f"API error after {max_retries} retries: {str(e)}. Giving up.")
                raise
            
            logger.warning(f"API error: {str(e)}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2
            retry_count += 1
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise 