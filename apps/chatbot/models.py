from django.db import models
from django.contrib.auth.models import User
from core.utils import generate_id

from ..workspaces.models import Workspace
from ..companies.models import CompanyProfile
# Create your models here.
class ChatMessage(models.Model):
    id = models.CharField(max_length=24, primary_key=True, default=generate_id)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='chat_messages')
    message = models.TextField()
    is_user_message = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{'User' if self.is_user_message else 'AI'}: {self.message[:30]}..."

class DocumentChunk(models.Model):
    id = models.CharField(max_length=24, primary_key=True, default=generate_id)
    text = models.TextField()
    embedding = models.TextField()
    source_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='document_chunks')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='document_chunks')

    def __str__(self):
        return f"DocumentChunk for {self.company.company_name}: {self.text[:30]}..."
