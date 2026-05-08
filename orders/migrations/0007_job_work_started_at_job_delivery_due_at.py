from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0006_job_allowed_reviews_job_reviews_used_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="work_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="delivery_due_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]