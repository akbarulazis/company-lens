import json
import logging
import traceback
from core.openai_client import openai_with_retry
from apps.compare.prompts import COMPANY_COMPARISON_SYSTEM_PROMPT, COMPANY_COMPARISON_USER_PROMPT

logger = logging.getLogger(__name__)

def generate_comparison_with_openai(companies_data):
    """Generate a comparison analysis using OpenAI"""
    try:
        # Create a prompt for the OpenAI model
        system_prompt = COMPANY_COMPARISON_SYSTEM_PROMPT + json.dumps(companies_data, indent=2)
        
        # Call the OpenAI API
        response = openai_with_retry(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": COMPANY_COMPARISON_USER_PROMPT}
            ],
            temperature=0.7,
            max_tokens=3000,
        )
        
        # Extract the generated content
        comparison_html = response.choices[0].message.content
        
        # Make sure it's properly formatted as HTML
        if not (comparison_html.strip().startswith('<') and comparison_html.strip().endswith('>')):
            comparison_html = f"<div class='comparison-content'>{comparison_html}</div>"
        
        return comparison_html
    
    except Exception as e:
        logger.error(f"Error in OpenAI comparison generation: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a simple comparison table as fallback
        fallback_html = "<div class='p-4 mb-4 text-red-700 bg-red-100 rounded-lg'>"
        fallback_html += "<h3 class='text-lg font-medium'>AI Comparison Failed</h3>"
        fallback_html += f"<p>We couldn't generate an AI comparison: {str(e)}</p>"
        fallback_html += "<p>Showing basic comparison data instead. You may try again or contact support if this issue persists.</p></div>"
        
        # Add a basic comparison table
        fallback_html += "<table class='w-full border-collapse'>"
        fallback_html += "<thead><tr><th class='border p-2'>Aspect</th>"
        
        # Add company names to header
        for company in companies_data:
            fallback_html += f"<th class='border p-2'>{company['name']}</th>"
        fallback_html += "</tr></thead><tbody>"
        
        # Add rows for different aspects
        aspects = [
            ('overall_score', 'Overall Score'),
            ('financial_health_score', 'Financial Health'),
            ('business_risk_score', 'Business Risk'),
            ('growth_potential_score', 'Growth Potential'),
            ('industry_position_score', 'Industry Position'),
            ('external_trends_score', 'External Trends')
        ]
        
        for key, label in aspects:
            fallback_html += f"<tr><td class='border p-2 font-medium'>{label}</td>"
            for company in companies_data:
                fallback_html += f"<td class='border p-2'>{company[key]}</td>"
            fallback_html += "</tr>"
        
        fallback_html += "</tbody></table>"
        return fallback_html
