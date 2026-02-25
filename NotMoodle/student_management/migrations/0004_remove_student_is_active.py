from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("student_management", "0003_student_user"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="student",
            name="is_active",
        ),
    ]