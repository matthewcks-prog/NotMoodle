from django.core.management.base import BaseCommand
from django.db import transaction

from student_management.models import Student, ManageCreditPoint
from lesson_management.models import LessonCreditAwarded, LessonEnrollment


class Command(BaseCommand):
    help = "Recalculate and backfill student credits based on passed lessons (core and electives). Creates LessonCreditAwarded records as needed."

    def add_arguments(self, parser):
        parser.add_argument("--student", type=int, help="Recalculate for a single student id")
        parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")

    def handle(self, *args, **options):
        student_id = options.get("student")
        dry_run = options.get("dry_run")

        qs = Student.objects.all()
        if student_id:
            qs = qs.filter(pk=student_id)

        total_students = qs.count()
        updated = 0
        created_awards = 0

        for student in qs.iterator():
            with transaction.atomic():
                # Compute credits from all PASSED lessons
                enrollments = LessonEnrollment.objects.filter(student=student).select_related("lesson")
                computed_credits = 0
                for e in enrollments:
                    passed, _, _ = e.lesson.student_passed(student)
                    if passed:
                        computed_credits += (e.lesson.lesson_credits or 0)
                        # Ensure an award record exists
                        if not LessonCreditAwarded.objects.filter(student=student, lesson=e.lesson).exists():
                            if not dry_run:
                                LessonCreditAwarded.objects.create(
                                    student=student,
                                    lesson=e.lesson,
                                    credits_amount=(e.lesson.lesson_credits or 0) or 0,
                                )
                            created_awards += 1

                credit, _ = ManageCreditPoint.objects.get_or_create(student=student)
                if credit.credits != computed_credits:
                    if not dry_run:
                        credit.credits = computed_credits
                        credit.save(update_fields=["credits"])
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Processed {total_students} students, updated credits for {updated} students, created {created_awards} award records"
        ))
