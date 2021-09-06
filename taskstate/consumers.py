import json
from datetime import timedelta

from channels.generic.websocket import WebsocketConsumer
from django.db import IntegrityError
from django.utils import timezone
from django.db.models import Case, Value, When

from taskstate.models import Task, Channel




class BaseAuthWebsocketConsumer(WebsocketConsumer):
    """
    A base websocket consumer that checks if the user is authenticated and
    if the user has any tasks. If not, this will close the connection.
    """
    text_data_json = None
    user = None

    def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            self.close()
        if not self.user.tasks.exists():
            self.close()
        self.accept()

    def receive(self, text_data):
        self.text_data_json = json.loads(text_data)
        pk_list = self.text_data_json.get('pk_list', None)
        if isinstance(pk_list, str) or isinstance(pk_list, int):
            pk_list = [pk_list]
        self.pk_list = pk_list




class SetTaskSeen(BaseAuthWebsocketConsumer):
    """
    A websocket consumer that enables a client to mark a task as seen.
    """

    def receive(self, text_data):
        super().receive(text_data)
        Task.set_seen_tasks(self.pk_list)




class CheckTaskStatus(BaseAuthWebsocketConsumer):
    """
    A websocket consumer that can be used to check/monitor a task's status.
    """

    def connect(self):
        super().connect()
        try:
            Channel.objects.create(name=self.channel_name)
        except IntegrityError:
            pass


    def disconnect(self, close_code):
        # Note that in some rare cases (power loss, etc)
        # disconnect may fail to run.
        Channel.objects.filter(name=self.channel_name).delete()


    def receive(self, text_data):
        super().receive(text_data)
        pk_list = self.pk_list

        channel = Channel.objects.get(
            name=self.channel_name,
        )
        channel.task_pk_list = pk_list
        channel.save()

        task_list = self.get_tasks(pk_list)

        # Need to send the results back immediately in case the task completes
        # very quickly. If the task is completed before this runs the results
        # will never reach the channel because we would not have had
        # enough time to create the channel object. No channel object means
        # that the signal receivers for `task_changed` and `post_save` won't
        # be able to find the right channel to send the status/progress to.
        self.send_tasks(task_list)


    def get_tasks(self, pk_list):
        task_list = Task.objects.filter(
            pk__in=pk_list,
            user=self.user,
            seen=False,
        )
        return task_list


    def send_tasks(self, task_list):
        self.send(text_data=json.dumps({
            'tasks': [
                {
                    'id': task.pk,
                    'pk': task.pk,
                    'status': task.status,
                    'progress': task.progress or '',
                    'description': task.description or '',
                }
                for task in task_list
            ],
        }))


    def task_status_update(self, event):
        pk_list = event['pk_list']
        task_list = self.get_tasks(pk_list)
        self.send_tasks(task_list)
