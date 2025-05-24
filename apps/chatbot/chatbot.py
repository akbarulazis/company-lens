import json
import logging
import os
from openai import OpenAI
from django.conf import settings
from dotenv import load_dotenv
from ..workspaces.models import Workspace
from ..companies.models import CompanyProfile, CompanyDocument
from .models import ChatMessage


load_dotenv()
logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class ChatbotRAG:
    def __init__(self, workspace_id):
        self.workspace_id = workspace_id
        self.model = "gpt-4o-mini"
        self.max_tokens = 1000

    def get_context(self, query):
        try:

            workspace = Workspace.objects.get(id=self.workspace_id)
            companies = CompanyProfile.objects.filter(workspace=workspace)

            if not companies:
                return "No companies found in this workspace."

            context = "COMPANY INFORMATION:\n\n"
            for company in companies:
                context += f"Company: {company.company_name}\n"
                context += f"Industry: {company.industry or 'Not specified'}\n"
                context += f"Profile: {company.profile_content[:1000]}...\n\n"


                if company.founded_year or company.headquarters or company.employee_count:
                    context += "Company Details:\n"
                    if company.founded_year:
                        context += f"- Founded: {company.founded_year}\n"
                    if company.headquarters:
                        context += f"- Headquarters: {company.headquarters}\n"
                    if company.employee_count:
                        context += f"- Employees: {company.employee_count}\n"
                    context += "\n"


                if company.market_cap or company.annual_revenue or company.funding_total:
                    context += "Financial Data:\n"
                    if company.market_cap:
                        context += f"- Market Cap: {company.market_cap}\n"
                    if company.annual_revenue:
                        context += f"- Annual Revenue: {company.annual_revenue}\n"
                    if company.funding_total:
                        context += f"- Total Funding: {company.funding_total}\n"
                    context += "\n"


                if company.overall_score > 0:
                    context += "Investment Scores:\n"
                    context += f"- Overall: {company.overall_score}\n"
                    context += f"- Financial Health: {company.financial_health_score}\n"
                    context += f"- Business Risk: {company.business_risk_score}\n"
                    context += f"- Growth Potential: {company.growth_potential_score}\n"
                    context += f"- Industry Position: {company.industry_position_score}\n"
                    context += f"- External Trends: {company.external_trends_score}\n"
                    context += "\n"


                competitors = company.competitors.all()
                if competitors:
                    context += "Competitors:\n"
                    for competitor in competitors:
                        context += f"- {competitor.competitor_name}\n"
                    context += "\n"

                executives = company.executives.all()
                if executives:
                    context += "Executive Team:\n"
                    for exec in executives:
                        context += f"- {exec.name} ({exec.position})\n"
                    context += "\n"


                funding_rounds = company.funding_rounds.all()
                if funding_rounds:
                    context += "Funding History:\n"
                    for round in funding_rounds:
                        context += f"- {round.round_type}: {round.amount} ({round.date})\n"
                    context += "\n"


                documents = company.documents.all()
                if documents:
                    context += "Document Key Points:\n"
                    for doc in documents:
                        if doc.key_points:
                            context += f"Document: {doc.title} ({doc.document_type})\n"
                            context += f"Key Points: {doc.key_points[:500]}...\n\n"

            return context

        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            return f"Error retrieving context: {str(e)}"

    def get_chat_history(self, limit=5):
        try:
            workspace = Workspace.objects.get(id=self.workspace_id)
            messages = ChatMessage.objects.filter(workspace=workspace).order_by('-created_at')[:limit]

            history = ""
            for message in reversed(messages):
                role = "User" if message.is_user_message else "Assistant"
                history += f"{role}: {message.message}\n\n"

            return history

        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
            return ""

    def generate_response(self, query):
        try:
            context = self.get_context(query)

            history = self.get_chat_history()

            prompt = f"""You are an AI assistant specialized in company research and financial analysis.
Answer the user's question based on the context provided about companies in the workspace.
Be precise, helpful, and concise.

FORMAT INSTRUCTIONS:
1. When listing multiple items, use proper HTML-like formatting with <ol> or <ul> list structures.
2. For market trends, use proper headings, bullet points, and clear separations between different trends.
3. Always use proper paragraph breaks for readability.
4. When comparing companies, use a clear structure with headings and subheadings.
5. Bold important points or company names using markdown format (**text**).

MARKET TRENDS FORMAT:
When discussing market trends affecting companies, use this structure:
- Start with a brief overview paragraph
- List each trend as a numbered item (1., 2., etc.)
- For each trend: Bold the trend name, then provide a concise explanation
- End with a concluding sentence or summary impact statement

Recent conversation:
{history}

CONTEXT INFORMATION:
{context}

User Question: {query}

Answer:"""


            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "You are a helpful assistant specialized in company research and financial analysis. Format your responses with clear structure and markdown formatting for readability."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.5
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"I'm sorry, I encountered an error processing your request: {str(e)}"

    def save_message(self, user, message, is_user_message=True):

        try:
            workspace = Workspace.objects.get(id=self.workspace_id)

            chat_message = ChatMessage(
                user=user,
                workspace=workspace,
                message=message,
                is_user_message=is_user_message
            )
            chat_message.save()

            return chat_message

        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return None