from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from ..workspaces.models import Workspace
from ..companies.models import CompanyProfile
from .models import ChatMessage
from .chatbot import ChatbotRAG
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logger = logging.getLogger(__name__)

# Create your views here.
@login_required
def chat_view(request, workspace_id):
    """View for the chatbot interface"""
    workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user)
    chat_history = ChatMessage.objects.filter(workspace=workspace).order_by('created_at')

    companies = CompanyProfile.objects.filter(workspace=workspace)
    
    logger.info(f"Chat view accessed for workspace: {workspace.name} with {companies.count()} companies")

    context = {
        'workspace': workspace,
        'chat_history': chat_history,
        'companies': companies
    }

    return render(request, 'chat.html', context)


@login_required
@csrf_exempt
def chat_message(request, workspace_id):
    """API endpoint for sending/receiving chat messages"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            
            logger.info(f"Chat message received: '{message[:50]}...' for workspace_id: {workspace_id}")

            # Initialize the chatbot
            chatbot = ChatbotRAG(workspace_id)

            # Check if companies exist in this workspace
            workspace = Workspace.objects.get(id=workspace_id)
            companies = CompanyProfile.objects.filter(workspace=workspace)
            if companies.count() == 0:
                logger.warning(f"No companies found in workspace {workspace.name} for chat message")
            else:
                logger.info(f"Found {companies.count()} companies in workspace {workspace.name} for chat message")
                for company in companies:
                    logger.info(f"Company in workspace: {company.company_name}")

            # Save the user message
            chatbot.save_message(request.user, message)

            # Generate a response with user context
            response = chatbot.generate_response(message, request.user)
            
            # Check if the response has the default rejection pattern
            if "I can only provide information about" in response and "companies in the workspace" in response:
                logger.warning("Response contains default rejection pattern despite having company data")
                # Create a better response
                company_names = ", ".join([company.company_name for company in companies])
                if companies.count() > 0:
                    response = f"""I have profile content for the following companies: {company_names}. 
                    
What would you like to know about these companies based on their profile content?"""

            # Save the assistant message
            chatbot.save_message(request.user, response, is_user_message=False)
            
            logger.info(f"Generated response: '{response[:50]}...'")

            return JsonResponse({
                'status': 'success',
                'response': response
            })

        except Exception as e:
            logger.error(f"Error in chat_message: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })
