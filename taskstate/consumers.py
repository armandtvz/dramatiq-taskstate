import json

from channels.generic.websocket import WebsocketConsumer
from django.db import IntegrityError

from taskstate.models import Task, Channel




class BaseAuthWebsocketConsumer(WebsocketConsumer):
    """
    A base websocket consumer that checks if the user is authenticated and
    if the user has any tasks. If not, this will close the connection.
    Creates a `Channel` object.
    """
    text_data_json = None
    user = None

    def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            self.close()
        if not self.user.tasks.exists():
            self.close()
        try:
            Channel.objects.create(name=self.channel_name)
        except IntegrityError:
            pass
        self.accept()

    def disconnect(self, close_code):
        # Note that in some rare cases (power loss, etc)
        # disconnect may fail to run.
        Channel.objects.filter(name=self.channel_name).delete()

    def receive(self, text_data):
        self.text_data_json = json.loads(text_data)




class CheckTaskStatus(BaseAuthWebsocketConsumer):
    """
    A websocket consumer that can be used to check/monitor a task's status.
    """
    groups = ['broadcast']

    def receive(self, text_data):
        super().receive(text_data)
        pk_list = self.text_data_json.get('pk_list', None)
        if isinstance(pk_list, str) or isinstance(pk_list, int):
            pk_list = [pk_list]
        else:
            self.close()

        channel = Channel.objects.get(
            name=self.channel_name,
        )
        channel.task_pk_list = pk_list
        channel.save()

        task_list = self.get_tasks(pk_list)
        self.set_task_seen(task_list)

        # Need to send the results back immediately in case the task completes
        # very quickly. If the task is completed before this runs the results
        # will never reach the channel because we would not have had
        # enough time to create the channel object. No channel object means
        # that the signal receivers for `task_changed` and `post_save` won't
        # be able to find the right channel to send the status/progress to.
        self.send(text_data=json.dumps({
            'tasks': [
                {
                    'id': task.pk,
                    'pk': task.pk,
                    'status': task.status,
                    'progress': task.progress or '',
                }
                for task in task_list
            ],
        }))


    def set_task_seen(self, task_list):
        for task in task_list:
            if task.is_complete:
                task.seen = True
        Task.objects.bulk_update(task_list, ['seen'])


    def get_tasks(self, pk_list):
        task_list = Task.objects.filter(pk__in=pk_list)
        return task_list


    def task_status_update(self, event):
        pk_list = event['pk_list']
        task_list = self.get_tasks(pk_list)
        self.send(text_data=json.dumps({
            'tasks': [
                {
                    'id': task.pk,
                    'pk': task.pk,
                    'status': task.status,
                    'progress': task.progress or '',
                }
                for task in task_list
            ],
        }))
