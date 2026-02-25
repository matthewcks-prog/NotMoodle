from django.core.management.base import BaseCommand
from lesson_management.models import Lesson

class Command(BaseCommand):
    help = "Set lesson_credits=6 for lessons currently set to 0 (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument('--only-published', action='store_true', help='Limit to published lessons')

    def handle(self, *args, **options):
        qs = Lesson.objects.filter(lesson_credits=0)
        if options.get('only_published'):
            qs = qs.filter(status='published')
        count = qs.count()
        updated = qs.update(lesson_credits=6)
        self.stdout.write(self.style.SUCCESS(f"Updated {updated}/{count} lessons to 6 credits"))
