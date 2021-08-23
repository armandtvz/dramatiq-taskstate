# Copied and changed from https://github.com/Bogdanp/django_dramatiq/blob/master/django_dramatiq/models.py

from datetime import timedelta

from django.db import models
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.db.models import Q
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

from dramatiq import Message
from django_dramatiq.apps import DjangoDramatiqConfig

#: The database label to use when storing task metadata.
DATABASE_LABEL = DjangoDramatiqConfig.tasks_database()




class TaskManager(models.Manager):
    def create_or_update_from_message(self, message, **extra_fields):
        task, created = self.using(DATABASE_LABEL).update_or_create(
            message_id=message.message_id,
            defaults={
                'message_data': message.encode(),
                **extra_fields,
            }
        )
        return task

    def delete_old_tasks(self, max_task_age):
        self.using(DATABASE_LABEL).filter(
            Q(status=Task.STATUS_DONE)
            | Q(status=Task.STATUS_FAILED)
            | Q(status=Task.STATUS_SKIPPED)
        ).filter(
            created_at__lte=now() - timedelta(seconds=max_task_age)
        ).filter(
            seen=True
        ).delete()

    def complete(self):
        return self.using(DATABASE_LABEL).filter(
            Q(status=Task.STATUS_DONE)
            | Q(status=Task.STATUS_FAILED)
            | Q(status=Task.STATUS_SKIPPED)
        )




class Task(models.Model):
    """
    Represents a Dramatiq background task.
    """
    STATUS_ENQUEUED = 'enqueued'
    STATUS_DELAYED = 'delayed'
    STATUS_RUNNING = 'running'
    STATUS_FAILED = 'failed'
    STATUS_DONE = 'done'
    STATUS_SKIPPED = 'skipped'
    STATUSES = [
        (STATUS_ENQUEUED, 'Enqueued'),
        (STATUS_DELAYED, 'Delayed'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_DONE, 'Done'),
        (STATUS_SKIPPED, 'Skipped'),
    ]

    message_id = models.UUIDField(unique=True)
    message_data = models.BinaryField()
    status = models.CharField(
        max_length=8,
        choices=STATUSES,
        default=STATUS_ENQUEUED,
    )
    actor_name = models.CharField(max_length=300, blank=True, null=True)
    queue_name = models.CharField(max_length=100, blank=True, null=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tasks',
    )
    description = models.CharField(max_length=255, blank=True, null=True)

    # Whether the task's final state has been seen by the user.
    seen = models.BooleanField(default=False)

    # The name of the model and app that this task might be related to
    model_name = models.CharField(max_length=255, blank=True, null=True)
    app_name = models.CharField(max_length=255, blank=True, null=True)

    progress = models.IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    tasks = TaskManager()
    objects = TaskManager()


    class Meta:
        ordering = ['-updated_at']
        default_permissions = []


    @cached_property
    def message(self):
        return Message.decode(bytes(self.message_data))


    def __str__(self):
        return str(self.message)
