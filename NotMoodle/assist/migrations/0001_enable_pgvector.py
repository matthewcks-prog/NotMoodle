"""Enable pgvector extension for PostgreSQL."""
from django.db import migrations, connection


def enable_pgvector(apps, schema_editor):
    """Only create extension on PostgreSQL."""
    if connection.vendor == 'postgresql':
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def disable_pgvector(apps, schema_editor):
    """Only drop extension on PostgreSQL."""
    if connection.vendor == 'postgresql':
        schema_editor.execute("DROP EXTENSION IF EXISTS vector;")


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(
            code=enable_pgvector,
            reverse_code=disable_pgvector,
        ),
    ]
