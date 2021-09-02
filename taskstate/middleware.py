import logging

from dramatiq.middleware import Middleware


logger = logging.getLogger('taskstate.StateMiddleware')




class StateMiddleware(Middleware):
    """
    This middleware keeps track of Dramatiq task executions only when
    you need it to. StateMiddleware checks for a keyword argument in the
    Dramatiq message called `for_state` which is a Python dictionary.
    The for_state dictionary can have the following keys:
    - user_pk
    - model_name
    - app_name
    - description

    These key-value pairs are saved to the `Task` object and can later be
    used to do a lookup on the Task objects to show the right tasks to
    the right users for specific things that the task is related to.

    For example:
    ```
    opts = SomeModel._meta
    Task.objects.filter(
        user=user.pk,
        app_name=opts.app_label,
        model_name
    )
    ```

    Each of these key-value pairs in the `for_state` dictionary are optional.
    The middleware only checks for the existence of this keyword argument.
    Therefore, if it's completely empty the task object will still be created
    and updated.
    """
    for_state = None

    def send_signal(self, task):
        from taskstate.signals import task_changed
        task_changed.send(
            sender=self.__class__,
            task=task,
        )


    def should_track(self, message):
        """
        Returns true if the task state can be tracked.
        """
        try:
            self.for_state = message.kwargs['for_state']
        except KeyError:
            return False

        if not isinstance(self.for_state, dict):
            logger.debug(
                'for_state value is not a dict, not tracking task state'
            )
            return False
        return True


    def get_user(self, message):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_pk = None
        user = None
        try:
            user_pk = self.for_state['user_pk']
        except KeyError:
            pass
        if user_pk:
            try:
                user = User.objects.get(pk=user_pk)
            except User.DoesNotExist:
                pass
        return user


    def after_enqueue(self, broker, message, delay):
        if not self.should_track(message):
            return
        from taskstate.models import Task
        user = self.get_user(message)
        logger.debug('Creating Task from message %r.', message.message_id)
        status = Task.STATUS_ENQUEUED
        if delay:
            status = Task.STATUS_DELAYED
        task = Task.objects.create_or_update_from_message(
            message,
            status=status,
            actor_name=message.actor_name,
            queue_name=message.queue_name,
            user=user,
            model_name=self.for_state.get('model_name', ''),
            app_name=self.for_state.get('app_name', ''),
            description=self.for_state.get('description', 'Task'),
        )
        self.send_signal(task)


    def before_process_message(self, broker, message):
        if not self.should_track(message):
            return
        from taskstate.models import Task
        user = self.get_user(message)
        logger.debug('Updating Task from message %r.', message.message_id)
        task = Task.objects.create_or_update_from_message(
            message,
            status=Task.STATUS_RUNNING,
            actor_name=message.actor_name,
            queue_name=message.queue_name,
            user=user,
            model_name=self.for_state.get('model_name', ''),
            app_name=self.for_state.get('app_name', ''),
            description=self.for_state.get('description', 'Task'),
        )
        self.send_signal(task)


    def after_skip_message(self, broker, message):
        from taskstate.models import Task
        self.after_process_message(broker, message, status=Task.STATUS_SKIPPED)


    def after_process_message(self, broker, message, *, result=None, exception=None, status=None):
        if not self.should_track(message):
            return
        from taskstate.models import Task
        user = self.get_user(message)

        if exception is not None:
            status = Task.STATUS_FAILED
        elif status is None:
            status = Task.STATUS_DONE

        logger.debug('Updating Task from message %r.', message.message_id)
        task = Task.objects.create_or_update_from_message(
            message,
            status=status,
            actor_name=message.actor_name,
            queue_name=message.queue_name,
            user=user,
            model_name=self.for_state.get('model_name', ''),
            app_name=self.for_state.get('app_name', ''),
            description=self.for_state.get('description', 'Task'),
        )
        self.send_signal(task)
