import json
import logging
from core.openai_client import openai_with_retry
from apps.compare.prompts import COMPANY_COMPARISON_SYSTEM_PROMPT, COMPANY_COMPARISON_USER_PROMPT

logger = logging.getLogger(__name__)

def generate_comparison_with_openai(companies_data):
    """Generate a comparison analysis using OpenAI"""
    try:
        # Create company names for title
        company_names = [company["name"] for company in companies_data]
        if len(company_names) == 2:
            title_text = f"Company Comparison: {company_names[0]} vs {company_names[1]}"
        else:
            title_text = f"Company Comparison: {', '.join(company_names[:-1])} and {company_names[-1]}"
        
        # Create prompt with company data
        system_prompt = COMPANY_COMPARISON_SYSTEM_PROMPT + json.dumps(companies_data, indent=2)
        
        # Call OpenAI API
        response = openai_with_retry(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": COMPANY_COMPARISON_USER_PROMPT}
            ],
            temperature=0.3,
            max_tokens=4000,
        )
        
        # Get and clean the response
        comparison_html = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if comparison_html.startswith("```html"):
            comparison_html = comparison_html[7:]
        if comparison_html.endswith("```"):
            comparison_html = comparison_html[:-3]
        
        # Add title if not present
        if "<h1" not in comparison_html.lower():
            comparison_html = f"<h1>{title_text}</h1>\n{comparison_html}"
            
        return comparison_html.strip()
    
    except Exception as e:
        logger.error(f"Error generating comparison: {str(e)}")
        
        # Simple fallback
        company_names = [company["name"] for company in companies_data]
        title = f"Company Comparison: {' vs '.join(company_names)}"
        
        fallback_html = f"""
        <h1>{title}</h1>
        <div class="error-message">
            <h3>Comparison Generation Failed</h3>
            <p>Unable to generate AI comparison. Please try again.</p>
        </div>
        
        <h2>Basic Comparison</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    {''.join(f'<th>{company["name"]}</th>' for company in companies_data)}
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Overall Score</td>
                    {''.join(f'<td>{company["overall_score"]}</td>' for company in companies_data)}
                </tr>
                <tr>
                    <td>Financial Health</td>
                    {''.join(f'<td>{company["financial_health_score"]}</td>' for company in companies_data)}
                </tr>
                <tr>
                    <td>Growth Potential</td>
                    {''.join(f'<td>{company["growth_potential_score"]}</td>' for company in companies_data)}
                </tr>
            </tbody>
        </table>
        """
        
        return fallback_html
