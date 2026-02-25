"""
Management command to index published lessons for RAG retrieval.

Usage:
    python manage.py index_lessons_for_rag [--lesson-id ID] [--force]
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from lesson_management.models import Lesson
from assist.models import DocumentChunk
from assist.ollama import embed_texts, estimate_tokens


class Command(BaseCommand):
    help = "Index published lessons by chunking and embedding their content for RAG"

    def add_arguments(self, parser):
        parser.add_argument(
            "--lesson-id",
            type=int,
            help="Index only this specific lesson ID",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-index lessons even if they already have chunks",
        )

    def handle(self, *args, **options):
        lesson_id = options.get("lesson_id")
        force = options.get("force", False)

        # Filter lessons
        lessons = Lesson.objects.filter(status="published")
        if lesson_id:
            lessons = lessons.filter(id=lesson_id)
        
        if not lessons.exists():
            self.stdout.write(self.style.WARNING("No published lessons found"))
            return

        total_chunks = 0
        total_lessons = 0

        for lesson in lessons:
            # Skip if already indexed (unless --force)
            existing_count = lesson.chunks.count()
            if existing_count > 0 and not force:
                self.stdout.write(
                    f"  Skipping {lesson.unit_code} (already has {existing_count} chunks)"
                )
                continue

            self.stdout.write(f"Processing {lesson.unit_code}: {lesson.title}")

            # Prepare content
            content = self._prepare_lesson_content(lesson)
            if not content.strip():
                self.stdout.write(self.style.WARNING(f"  No content found for {lesson.unit_code}"))
                continue

            # Chunk the content
            chunks = self._chunk_text(content)
            self.stdout.write(f"  Created {len(chunks)} chunks")

            # Generate embeddings
            try:
                embeddings = embed_texts(chunks)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  Failed to generate embeddings: {e}")
                )
                continue

            # Save chunks to database
            with transaction.atomic():
                # Delete old chunks if re-indexing
                if force and existing_count > 0:
                    lesson.chunks.all().delete()
                    self.stdout.write(f"  Deleted {existing_count} old chunks")

                # Create new chunks
                chunk_objects = []
                for chunk_text, embedding in zip(chunks, embeddings):
                    chunk_objects.append(
                        DocumentChunk(
                            lesson=lesson,
                            content=chunk_text,
                            embedding=embedding,
                            token_count=estimate_tokens(chunk_text),
                        )
                    )
                
                DocumentChunk.objects.bulk_create(chunk_objects)
                self.stdout.write(
                    self.style.SUCCESS(f"  Saved {len(chunk_objects)} chunks")
                )
                total_chunks += len(chunk_objects)
                total_lessons += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nIndexing complete: {total_lessons} lessons, {total_chunks} total chunks"
            )
        )

    def _prepare_lesson_content(self, lesson) -> str:
        """
        Extract and combine all text content from a lesson.
        
        Args:
            lesson: Lesson model instance
        
        Returns:
            Combined text content
        """
        parts = [
            f"Unit Code: {lesson.unit_code}",
            f"Title: {lesson.title}",
        ]
        
        if lesson.description:
            parts.append(f"Description: {lesson.description}")
        
        if lesson.objectives:
            parts.append(f"Learning Objectives: {lesson.objectives}")
        
        # Add reading list if available
        try:
            reading_lists = lesson.reading_lists.all()
            for rl in reading_lists:
                parts.append(f"Reading: {rl.title} - {rl.description}")
        except:
            pass
        
        return "\n\n".join(parts)

    def _chunk_text(self, text: str, target_chars: int = 1200, overlap: int = 200) -> list[str]:
        """
        Split text into overlapping chunks.
        
        Aims for ~800-1200 chars per chunk (roughly 200-300 tokens).
        Uses simple paragraph-based splitting with overlap for context continuity.
        
        Args:
            text: Text to chunk
            target_chars: Target characters per chunk
            overlap: Characters to overlap between chunks
        
        Returns:
            List of text chunks
        """
        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_len = len(para)
            
            # If single paragraph exceeds target, split it
            if para_len > target_chars * 1.5:
                # Save current chunk if any
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split long paragraph by sentences
                sentences = para.split(". ")
                temp_chunk = []
                temp_len = 0
                
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    sent_len = len(sent) + 2  # +2 for ". "
                    
                    if temp_len + sent_len > target_chars and temp_chunk:
                        chunks.append(". ".join(temp_chunk) + ".")
                        # Keep last sentence for overlap
                        temp_chunk = [temp_chunk[-1], sent]
                        temp_len = len(temp_chunk[-2]) + sent_len
                    else:
                        temp_chunk.append(sent)
                        temp_len += sent_len
                
                if temp_chunk:
                    chunks.append(". ".join(temp_chunk) + ".")
                continue
            
            # Check if adding this paragraph exceeds target
            if current_length + para_len > target_chars and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                
                # Keep last paragraph for overlap if small enough
                if len(current_chunk[-1]) < overlap:
                    current_chunk = [current_chunk[-1], para]
                    current_length = len(current_chunk[-1]) + para_len
                else:
                    current_chunk = [para]
                    current_length = para_len
            else:
                current_chunk.append(para)
                current_length += para_len + 2  # +2 for "\n\n"
        
        # Add remaining chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        return chunks
