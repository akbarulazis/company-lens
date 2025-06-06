# Generated by Django 5.2.1 on 2025-05-23 00:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0001_initial'),
        ('workspaces', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='companyprofile',
                    name='workspace',
                    field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='companies', to='workspaces.workspace'),
                ),
                migrations.AddField(
                    model_name='companydocument',
                    name='company',
                    field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='companies.companyprofile'),
                ),
            ],
        ),
    ]
