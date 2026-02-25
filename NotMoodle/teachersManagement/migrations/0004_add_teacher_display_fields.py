from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("teachersManagement", "0003_delete_teacher"),
    ]

    operations = [
        migrations.AddField(
            model_name="teacherprofile",
            name="display_name",
            field=models.CharField(
                blank=True, 
                help_text="Full display name for the teacher", 
                max_length=200
            ),
        ),
        migrations.AddField(
            model_name="teacherprofile",
            name="contact_email",
            field=models.EmailField(
                blank=True, 
                help_text="Primary contact email for the teacher"
            ),
        ),
    ]