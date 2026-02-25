from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ("course_management", "0005_alter_course_options_and_more"),
        ("teachersManagement", "0003_delete_teacher"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="director",
            field=models.ForeignKey(
                blank=True, 
                help_text="Teacher responsible for directing this course", 
                null=True, 
                on_delete=django.db.models.deletion.SET_NULL, 
                related_name="directed_courses", 
                to="teachersManagement.teacherprofile"
            ),
        ),
    ]