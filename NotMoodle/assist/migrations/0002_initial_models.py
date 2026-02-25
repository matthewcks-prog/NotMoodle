"""Initial models for assist app."""
# Generated migration - models for DocumentChunk and StudentQuestion
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import pgvector.django


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('assist', '0001_enable_pgvector'),
        ('lesson_management', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(help_text='Text content of this chunk')),
                ('embedding', pgvector.django.VectorField(dimensions=768, help_text='Vector embedding for semantic search')),
                ('token_count', models.IntegerField(default=0, help_text='Approximate token count for this chunk')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='lesson_management.lesson')),
            ],
            options={
                'ordering': ['lesson', 'id'],
            },
        ),
        migrations.CreateModel(
            name='StudentQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField(help_text="Student's question")),
                ('answer', models.TextField(help_text="AI assistant's answer")),
                ('tokens_in', models.IntegerField(default=0, help_text='Approximate input tokens')),
                ('tokens_out', models.IntegerField(default=0, help_text='Approximate output tokens')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_questions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='documentchunk',
            index=models.Index(fields=['lesson', '-created_at'], name='assist_docu_lesson__a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='studentquestion',
            index=models.Index(fields=['user', '-created_at'], name='assist_stud_user_id_d4e5f6_idx'),
        ),
    ]
