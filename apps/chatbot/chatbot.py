import json
import logging
import os
import numpy as np
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
        self.embedding_model = "text-embedding-3-small"
        self.max_tokens = 1000
        self.company_data = None
        self.company_embeddings = None

    def get_context(self, query):
        try:
            # If we haven't loaded company data yet, do it now
            if self.company_data is None or self.company_embeddings is None:
                self._prepare_company_data()

            # Get workspace and companies for logging
            workspace = Workspace.objects.get(id=self.workspace_id)
            companies = CompanyProfile.objects.filter(workspace=workspace)

            # Log information about the companies found
            logger.info(f"Found {companies.count()} companies in workspace {workspace.name}")
            for company in companies:
                logger.info(f"Company found: {company.company_name}, Industry: {company.industry}")
            
            # Generate embedding for the query
            query_embedding = self._generate_embedding(query)
            
            # Find most relevant context using similarity search
            if query_embedding and self.company_embeddings and len(self.company_embeddings) > 0:
                logger.info(f"Finding similar contexts for query: '{query}' among {len(self.company_embeddings)} chunks")
                most_relevant_contexts = self._find_similar_contexts(query_embedding)
                if most_relevant_contexts:
                    logger.info("Found relevant contexts through similarity search")
                    return most_relevant_contexts
                else:
                    logger.warning("No relevant contexts found through similarity search")
            else:
                if not query_embedding:
                    logger.warning("Failed to generate query embedding")
                if not self.company_embeddings or len(self.company_embeddings) == 0:
                    logger.warning(f"No company embeddings available. company_data: {len(self.company_data) if self.company_data else 0}, company_embeddings: {len(self.company_embeddings) if self.company_embeddings else 0}")
            
            # Fallback: return all company data
            logger.info("Using fallback method to get context")

            if not companies.exists():
                logger.warning("No companies found in workspace")
                return "No companies found in this workspace."

            context = "COMPANY INFORMATION:\n\n"
            for company in companies:
                context += f"Company: {company.company_name}\n"
                context += f"Industry: {company.industry or 'Not specified'}\n"
                context += f"Profile: {company.profile_content[:1000] if company.profile_content else 'No profile available'}...\n\n"

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

            # Log the first part of the context to check it's not empty
            logger.info(f"Context preview: {context[:200]}...")
            return context

        except Exception as e:
            logger.error(f"Error getting context: {str(e)}", exc_info=True)
            return f"Error retrieving context: {str(e)}"
    
    def _prepare_company_data(self):
        """Prepare company data and their embeddings for similarity search"""
        try:
            workspace = Workspace.objects.get(id=self.workspace_id)
            companies = CompanyProfile.objects.filter(workspace=workspace)
            
            logger.info(f"Preparing data for {companies.count()} companies in workspace {workspace.name}")
            
            self.company_data = []
            self.company_embeddings = []
            
            # Create chunks from company data
            for company in companies:
                # Basic company info
                chunk = f"Company: {company.company_name}\n"
                chunk += f"Industry: {company.industry or 'Not specified'}\n"
                chunk += f"Profile: {company.profile_content[:1000] if company.profile_content else 'No profile available'}\n"
                self.company_data.append(chunk)
                
                # Company details
                if company.founded_year or company.headquarters or company.employee_count:
                    chunk = f"Company: {company.company_name} - Details\n"
                    if company.founded_year:
                        chunk += f"Founded: {company.founded_year}\n"
                    if company.headquarters:
                        chunk += f"Headquarters: {company.headquarters}\n"
                    if company.employee_count:
                        chunk += f"Employees: {company.employee_count}\n"
                    self.company_data.append(chunk)
                
                # Financial data
                if company.market_cap or company.annual_revenue or company.funding_total:
                    chunk = f"Company: {company.company_name} - Financial Data\n"
                    if company.market_cap:
                        chunk += f"Market Cap: {company.market_cap}\n"
                    if company.annual_revenue:
                        chunk += f"Annual Revenue: {company.annual_revenue}\n"
                    if company.funding_total:
                        chunk += f"Total Funding: {company.funding_total}\n"
                    self.company_data.append(chunk)
                
                # Investment scores
                if company.overall_score > 0:
                    chunk = f"Company: {company.company_name} - Investment Scores\n"
                    chunk += f"Overall Score: {company.overall_score}\n"
                    chunk += f"Financial Health: {company.financial_health_score}\n"
                    chunk += f"Business Risk: {company.business_risk_score}\n"
                    chunk += f"Growth Potential: {company.growth_potential_score}\n"
                    chunk += f"Industry Position: {company.industry_position_score}\n"
                    chunk += f"External Trends: {company.external_trends_score}\n"
                    self.company_data.append(chunk)
                
                # Competitors
                competitors = company.competitors.all()
                if competitors:
                    chunk = f"Company: {company.company_name} - Competitors\n"
                    for competitor in competitors:
                        chunk += f"- {competitor.competitor_name}\n"
                    self.company_data.append(chunk)
                
                # Executive team
                executives = company.executives.all()
                if executives:
                    chunk = f"Company: {company.company_name} - Executive Team\n"
                    for exec in executives:
                        chunk += f"- {exec.name} ({exec.position})\n"
                    self.company_data.append(chunk)
                
                # Funding history
                funding_rounds = company.funding_rounds.all()
                if funding_rounds:
                    chunk = f"Company: {company.company_name} - Funding History\n"
                    for round in funding_rounds:
                        chunk += f"- {round.round_type}: {round.amount} ({round.date})\n"
                    self.company_data.append(chunk)
                
                # Documents
                documents = company.documents.all()
                if documents:
                    for doc in documents:
                        if doc.key_points:
                            chunk = f"Company: {company.company_name} - Document: {doc.title} ({doc.document_type})\n"
                            chunk += f"Key Points: {doc.key_points[:1000]}\n"
                            self.company_data.append(chunk)
            
            logger.info(f"Created {len(self.company_data)} data chunks")
            
            # Generate embeddings for all chunks
            if len(self.company_data) > 0:
                logger.info(f"Generating embeddings for {len(self.company_data)} chunks")
                for chunk in self.company_data:
                    embedding = self._generate_embedding(chunk)
                    if embedding:
                        self.company_embeddings.append(embedding)
                    else:
                        # If embedding failed, add a placeholder to maintain alignment
                        logger.warning(f"Failed to generate embedding for chunk: {chunk[:100]}...")
                        self.company_embeddings.append([0] * 1536)
                
                logger.info(f"Generated {len(self.company_embeddings)} embeddings")
            else:
                logger.warning("No company data chunks to embed")
            
        except Exception as e:
            logger.error(f"Error preparing company data: {str(e)}", exc_info=True)
            self.company_data = []
            self.company_embeddings = []
    
    def _generate_embedding(self, text):
        """Generate an embedding for the given text using OpenAI's API"""
        try:
            if not text:
                logger.warning("Empty text provided for embedding generation")
                return None
                
            response = client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}", exc_info=True)
            return None
    
    def _find_similar_contexts(self, query_embedding, top_k=5):
        """Find the most similar contexts for a given query embedding"""
        if not self.company_data or not self.company_embeddings or len(self.company_data) != len(self.company_embeddings):
            logger.warning(f"Cannot find similar contexts. company_data: {len(self.company_data) if self.company_data else 0}, company_embeddings: {len(self.company_embeddings) if self.company_embeddings else 0}")
            return None
        
        similarities = []
        for i, embedding in enumerate(self.company_embeddings):
            similarity = self._cosine_similarity(query_embedding, embedding)
            similarities.append((i, similarity))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get the top_k most similar contexts
        most_relevant = []
        for i, similarity in similarities[:top_k]:
            if similarity > 0.5:  # Only include if similarity is reasonably high
                most_relevant.append(f"{self.company_data[i]}\nRelevance: {similarity:.4f}")
        
        logger.info(f"Found {len(most_relevant)} relevant contexts with similarity > 0.5")
        
        if not most_relevant:
            logger.warning("No contexts with similarity > 0.5 found")
            # Fallback: include at least some contexts even with lower similarity
            for i, similarity in similarities[:3]:
                most_relevant.append(f"{self.company_data[i]}\nRelevance: {similarity:.4f}")
            logger.info(f"Added {len(most_relevant)} fallback contexts with lower similarity")
        
        return "\n\n".join(most_relevant)
    
    def _cosine_similarity(self, a, b):
        """Calculate cosine similarity between two vectors"""
        try:
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {str(e)}", exc_info=True)
            return 0.0

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
            logger.error(f"Error getting chat history: {str(e)}", exc_info=True)
            return ""

    def generate_response(self, query):
        try:
            logger.info(f"Generating response for query: '{query}'")
            
            # Get company information
            workspace = Workspace.objects.get(id=self.workspace_id)
            companies = CompanyProfile.objects.filter(workspace=workspace)
            
            # Get context with company information
            context = self.get_context(query)

            # Log if context is empty or very short
            if not context or len(context) < 50:
                logger.warning(f"Context is very short or empty: '{context}'")
            
            # Get chat history
            history = self.get_chat_history()

            # Check if we have any companies in the workspace
            company_count = companies.count()
            logger.info(f"Found {company_count} companies in workspace {workspace.name}")
            
            if company_count == 0:
                logger.warning("No companies in workspace, will generate a response indicating this")
                return "I don't have any company information in this workspace to provide you with. Please add some companies to the workspace first."
            
            # Create a list of company names for the system message
            company_names = ", ".join([company.company_name for company in companies])
            
            prompt = f"""You are a specialized AI assistant focused on providing information about companies in the user's workspace.
Your sole purpose is to answer questions based on the company information provided.

IMPORTANT RULES:
1. The companies in the workspace are: {company_names}
2. You should answer the user's question using ONLY the information in the context provided below.
3. Do NOT make up or hallucinate any information that's not in the context.
4. If you don't have enough information in the context to answer fully, acknowledge the limitations in your knowledge.
5. Do NOT say that you can only provide information about companies in the workspace - you already have company information.
6. If the user asks about a topic unrelated to the companies in the workspace, explain that you can help with questions about {company_names}.

FORMAT INSTRUCTIONS:
1. Use clear section headings with "### " prefix for major sections.
2. Make company names and important terms bold with ** markdown (e.g., **{company_names}**).
3. Use proper numbered lists for sequential items and bullet points for non-sequential items.
4. Structure your content with clear paragraphs, leaving empty lines between sections.
5. When listing features or characteristics, use a numbered format with descriptive titles.

Recent conversation:
{history}

CONTEXT INFORMATION:
{context}

User Question: {query}

Answer:"""

            system_message = f"""You are a helpful assistant specialized in company research and financial analysis. 
Format your responses with clear structure and markdown formatting for readability. 
The workspace contains information about these companies: {company_names}. 
Use the context provided to answer questions about these companies.
Do NOT respond that you can only answer questions about companies in the workspace - you already have that information."""

            logger.info(f"Sending request to OpenAI with prompt length: {len(prompt)}")

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.5
            )

            answer = response.choices[0].message.content
            logger.info(f"Generated response of length: {len(answer)}")
            
            # Check if the response has the default rejection pattern
            if "I can only provide information about" in answer and "companies in the workspace" in answer:
                logger.warning("Response contains default rejection pattern despite having company data")
                # Override with a more helpful response
                answer = f"""I have information about the following companies: {company_names}. 
                
What specific details would you like to know about these companies? I can provide information about their industry, financial data, executives, and more."""
            
            return answer

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
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
            logger.error(f"Error saving message: {str(e)}", exc_info=True)
            return None