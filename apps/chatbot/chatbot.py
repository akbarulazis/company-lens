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

    def get_context(self, query, user=None):
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

            # Add user profile information to context
            context = ""
            if user:
                context += "USER PROFILE INFORMATION:\n\n"
                context += f"User: {user.first_name} {user.last_name}\n"
                context += f"Username: {user.username}\n"
                context += f"Email: {user.email}\n"
                context += f"Workspace: {workspace.name}\n"
                if workspace.description:
                    context += f"Workspace Description: {workspace.description}\n"
                context += "\n"

            context += "COMPANY INFORMATION:\n\n"
            for company in companies:
                context += f"Company: {company.company_name}\n"
                context += f"Industry: {company.industry or 'Not specified'}\n"
                context += f"Profile Content: {company.profile_content if company.profile_content else 'No profile available'}\n\n"

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
                # Only use company name, industry, and profile content
                chunk = f"Company: {company.company_name}\n"
                chunk += f"Industry: {company.industry or 'Not specified'}\n"
                
                # Split profile content into smaller chunks if it's large
                if company.profile_content:
                    # If profile content is very long, split it into chunks of ~1000 characters
                    profile_content = company.profile_content
                    if len(profile_content) > 1500:
                        # Process content in chunks
                        for i in range(0, len(profile_content), 1000):
                            content_chunk = profile_content[i:i+1000]
                            section_chunk = f"Company: {company.company_name}\n"
                            section_chunk += f"Industry: {company.industry or 'Not specified'}\n"
                            section_chunk += f"Profile Content (Part {i//1000 + 1}): {content_chunk}\n"
                            self.company_data.append(section_chunk)
                    else:
                        # Small enough to be one chunk
                        chunk += f"Profile Content: {profile_content}\n"
                        self.company_data.append(chunk)
                else:
                    # No profile content
                    chunk += "Profile Content: No profile available\n"
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

    def generate_response(self, query, user=None):
        try:
            logger.info(f"Generating response for query: '{query}'")
            
            # Get company information
            workspace = Workspace.objects.get(id=self.workspace_id)
            companies = CompanyProfile.objects.filter(workspace=workspace)
            
            # Get context with company and user information
            context = self.get_context(query, user)

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
            
            # Create user context string for the prompt
            user_context = ""
            if user:
                user_context = f"You are assisting {user.first_name} {user.last_name} (@{user.username}) in their workspace '{workspace.name}'. "
                if workspace.description:
                    user_context += f"This workspace is described as: {workspace.description}. "

            prompt = f"""{user_context}You are a specialized AI assistant focused on providing information about companies in the user's workspace.
Your sole purpose is to answer questions based on the company profile content provided.

IMPORTANT RULES:
1. The companies in the workspace are: {company_names}
2. You should answer the user's question using ONLY the information in the profile content provided in the context below.
3. Do NOT make up or hallucinate any information that's not in the profile content.
4. If you don't have enough information in the profile content to answer fully, acknowledge the limitations in your knowledge.
5. Do NOT say that you can only provide information about companies in the workspace - you already have company information.
6. If the user asks about a topic unrelated to the companies in the workspace, explain that you can help with questions about {company_names}.
7. You can personalize your responses by referring to the user by their first name when appropriate.
8. Focus on extracting relevant information from the company profile content to answer questions.

FORMAT INSTRUCTIONS:
1. Use clear section headings with "### " prefix for major sections.
2. Make company names and important terms bold with ** markdown (e.g., **{company_names}**).
3. Use proper numbered lists for sequential items and bullet points for non-sequential items.
4. Structure your content with clear paragraphs, leaving empty lines between sections.
# 5. When listing features or characteristics, use a numbered format with descriptive titles.

Recent conversation:
{history}

CONTEXT INFORMATION:
{context}

User Question: {query}

Answer:"""

            system_message = f"""You are a helpful assistant specialized in analyzing company profile information. 
Format your responses with clear structure and markdown formatting for readability. 
The workspace contains profile content for these companies: {company_names}. 
Use the profile content provided in the context to answer questions about these companies.
{f"You are assisting {user.first_name} {user.last_name} - personalize your responses when appropriate." if user else ""}
Do NOT respond that you can only answer questions about companies in the workspace - you already have that information.
Focus on providing insights based on the company profile content only."""

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