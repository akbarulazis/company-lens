from django.contrib import admin
from .models import Company, CompanyProfile, CompanyDocument

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'ticker', 'created_at')
    search_fields = ('name', 'ticker')
    list_filter = ('created_at',)

admin.site.register(CompanyProfile)
admin.site.register(CompanyDocument)