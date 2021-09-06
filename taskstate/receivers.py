from django.dispatch import receiver
from django.db.models.signals import post_save

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from taskstate.middleware import StateMiddleware
from taskstate.signals import task_changed
from taskstate.models import Task, Channel




def send_to_channel(task):
    """
    A task was updated by Dramatiq's middleware.
    This sends the task to the relevant channel (django-channels) websocket.
    """
    channels = Channel.objects.filter(
        task_pk_list__contains=[task.pk],
    )
    channel_layer = get_channel_layer()
    for channel in channels:
        async_to_sync(channel_layer.send)(channel.name, {
            'type': 'task.status.update',
            'pk_list': channel.task_pk_list,
        })




@receiver(post_save, sender=Task)
def handle_task_saved(sender, instance, created, **kwargs):
    if not created: # not on first save
        task = instance
        if task.progress:
            if task.progress % 10 == 0:
                send_to_channel(task)




@receiver(task_changed, sender=StateMiddleware)
def handle_task_changed(sender, task, **kwargs):
    send_to_channel(task)
