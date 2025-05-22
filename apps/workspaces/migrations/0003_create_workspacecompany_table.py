from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0002_companyprofile_companydocument'),
        ('workspaces', '0002_rename_added_at_workspacecompany_created_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkspaceCompany',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='companies.company')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='workspaces.workspace')),
            ],
            options={
                'unique_together': {('workspace', 'company')},
            },
        ),
    ] 