"""Add vector similarity index for fast nearest-neighbor search."""
from django.db import migrations, connection


def create_vector_index(apps, schema_editor):
    """Only create vector index on PostgreSQL."""
    if connection.vendor == 'postgresql':
        schema_editor.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS assist_documentchunk_embedding_ivfflat_idx
            ON assist_documentchunk USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)


def drop_vector_index(apps, schema_editor):
    """Only drop vector index on PostgreSQL."""
    if connection.vendor == 'postgresql':
        schema_editor.execute("""
            DROP INDEX CONCURRENTLY IF EXISTS assist_documentchunk_embedding_ivfflat_idx;
        """)


class Migration(migrations.Migration):
    # CONCURRENTLY operations cannot run inside a transaction
    atomic = False

    dependencies = [
        ('assist', '0002_initial_models'),
    ]

    operations = [
        migrations.RunPython(
            code=create_vector_index,
            reverse_code=drop_vector_index,
        ),
    ]
