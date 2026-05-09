from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0008_mentor_mentorshipsession'),
    ]

    operations = [
        migrations.AddField(
            model_name='mentorshipsession',
            name='scheduled_time',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
