from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from ..workspaces.models import Workspace
from ..companies.models import CompanyProfile
from .models import ChatMessage
from .chatbot import ChatbotRAG
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
# Create your views here.
@login_required
def chat_view(request, workspace_id):
    """View for the chatbot interface"""
    workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user)
    chat_history = ChatMessage.objects.filter(workspace=workspace).order_by('created_at')

    companies = CompanyProfile.objects.filter(workspace=workspace)

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

            # Initialize the chatbot
            chatbot = ChatbotRAG(workspace_id)

            # Save the user message
            chatbot.save_message(request.user, message)

            # Generate a response
            response = chatbot.generate_response(message)

            # Save the assistant message
            chatbot.save_message(request.user, response, is_user_message=False)

            return JsonResponse({
                'status': 'success',
                'response': response
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })
