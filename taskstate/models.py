# Copied and changed from https://github.com/Bogdanp/django_dramatiq/blob/master/django_dramatiq/models.py

from datetime import timedelta

from django.db import models
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.db.models import Q
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField

from dramatiq import Message
from django_dramatiq.apps import DjangoDramatiqConfig

# The database label to use when storing task metadata.
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


    def delete_old_tasks(self, max_task_age, only_if_seen=True):
        """
        Deletes task objects when:
        - Tasks with done status.
        - Tasks with failed status.
        - Tasks with skipped status.
        - created_date is less than or equal to: now - max_task_age
        - If `only_if_seen` keyword argument is set then it will only
          delete a task if it has been marked as seen.
        """
        tasks = self.completed().filter(
            created_date__lte=now() - timedelta(seconds=max_task_age)
        )
        if only_if_seen:
            tasks = tasks.filter(seen=True)
        tasks.delete()


    def completed(self):
        return self.using(DATABASE_LABEL).filter(
            Q(status=Task.STATUS_DONE)
            | Q(status=Task.STATUS_FAILED)
            | Q(status=Task.STATUS_SKIPPED)
        )




class Task(models.Model):
    """
    Represents a Dramatiq background task.
    Possible statuses are:
    - enqueued
    - delayed
    - running
    - failed
    - done
    - skipped
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
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
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
        default=0,
    )
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True, db_index=True)

    objects = TaskManager()


    class Meta:
        ordering = ['-last_modified']
        default_permissions = []


    @cached_property
    def message(self):
        return Message.decode(bytes(self.message_data))


    def __str__(self):
        return str(self.message)




class ChannelManager(models.Manager):

    def delete_old(self, max_age=604800):
        """
        Will delete all channels older than or equal to the `max_age`
        argument value which is 604800 seconds by default. 604800 seconds
        is equal to 7 days.
        """
        channels = self.filter(
            created_date__lte=now() - timedelta(seconds=max_age)
        )
        channels.delete()




class Channel(models.Model):
    """
    Represents a channel in django-channels.
    This is to be used specifically with the Task model as
    it is only created to help report the state of a task
    to a request. The channel name is saved in this object;
    then retrieved again to send the task status to the
    correct channel.
    """
    name = models.CharField(max_length=255, unique=True)
    task_pk_list = ArrayField(
        base_field=models.BigIntegerField(),
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='task_channels',
    )
    last_modified = models.DateTimeField(auto_now=True)
    created_date = models.DateTimeField(auto_now_add=True)

    objects = ChannelManager()

    class Meta:
        default_permissions = []

    def __str__(self):
        return self.name
