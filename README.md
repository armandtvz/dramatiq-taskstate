# dramatiq-taskstate
A middleware for Dramatiq (for Django) that keeps track of task state only
when you need it to.


## Note:
When using the term "task" in the documentation: that would generally refer
to the task model in this package. It has nothing to do with Dramatiq or the
`django_dramatiq` package except that the `Task` model is an abstraction of
a Dramatiq task. Therefore, this package only operates on the `Task` model
and not Dramatiq tasks.


## Quickstart
1. Install dramatiq-taskstate via pip:
   ```
   pip install dramatiq-taskstate
   ```

1. Add `taskstate` and `django.contrib.postgres` to your `INSTALLED_APPS` in
   your project settings.py file:
   ```python
   INSTALLED_APPS = [
       'django_dramatiq',
       '...',
       'django.contrib.postgres',
       '...',
       'taskstate',
   ]
   ```

1. Run migrate:
   ```
   python manage.py migrate
   ```

1. Include the middleware in your `django_dramatiq` configuration:
    ```python
    DRAMATIQ_BROKER = {
        'BROKER': '...',
        'OPTIONS': {
            # ...
        },
        'MIDDLEWARE': [
            # ...
            'taskstate.middleware.StateMiddleware',
        ]
    }
    ```

1. Add a `for_state` parameter to Dramatiq actors that need task state
   to be tracked. The middleware will ignore any tasks that don't have
   this argument. Also remember that all values in the `for_state`
   dictionary must be JSON serializable.
   ```python
   @dramatiq.actor
   def my_actor(arg, for_state={}):
       pass
   ```

1. Then, when sending a new task to Dramatiq: the `for_state` dictionary can
   contain any of the following keys:
   ```python
   'for_state': {
       'user_pk': user.pk,
       'model_name': 'model',
       'app_name': 'app',
       'description': 'description',
   }
   ```

1. Each time a task's status is updated a `task_changed` signal is dispatched
   which can be handled like this:
   ```python
   from django.dispatch import receiver

   from taskstate.middleware import StateMiddleware
   from taskstate.signals import task_changed

   @receiver(task_changed, sender=StateMiddleware)
   def handle_task_changed(sender, task, **kwargs):
       pass
   ```
   Keep in mind that this is not a `post_save` signal -- it only fires for
   status updates.




## Reporting task state to the UI
Of course, a common case with background tasks is that the progress/state of a
task needs to be displayed to a user somehow. This package includes a
`WebsocketConsumer` that can be used with [django-channels][1] to check the
status of a task. Check the flowchart in the root of the repo for more
information on how this works.

Check the `get_task_status.js` file in the `taskstate/static` directory for
an example of how to send a request via websockets to get/monitor the task
status/progress. Also, as shown in the flowchart in the root of the repo,
both `task_changed` -- which only handles when the task object's status is
updated, i.e, enqueued, done, etc. -- and `post_save` signals are handled.

Routing is included for django-channels. Make sure to use the [URLRouter][2]
for your django-channels configuration. You can send data for the
websocket to the following route:
```
/ws/get-task-status/
```

Or, create your own route:
```python
from django.urls import re_path

from taskstate.consumers import CheckTaskStatus

websocket_urlpatterns = [
    re_path(r'^ws/custom-route-task-status/$', CheckTaskStatus.as_asgi()),
]
```

Also remember to add the routes to your django-channels router, for example:
```python
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                taskstate.routing.websocket_urlpatterns,
            )
        ),
    ),
})
```

A default template is included to render tasks in the UI -- use the following
in your templates (check the template to see which context variables to use):
```
{% include 'taskstate/task_list.html' %}
```

The above template will merely render a list of tasks, however, to check/monitor
the statuses of those tasks include the default script in your HTML before
the closing body tag:
```html
<script src="{% static 'taskstate/get_task_status.js' %}" charset="utf-8"></script>
```




## Updating progress percentage of a `Task`
See the `task_progress_example.py` file in the examples directory in the root of
the repo for an example of how to update the progress of a task. Note that
some of the details there are specific to Dramatiq itself.




## Seen status of a `Task`
A task can only be marked as seen when it is complete. The seen status of a
set of tasks can be set through another django-channels route:
```
/ws/set-task-seen/
```

Sending a list of task ID's to this route will automatically mark all
completed tasks from the list of ID's as seen. This is handled in the default
JS script -- therefore, check the `get_task_status.js` file for an example.

There is also an APS (Advanced Python Scheduler) periodic task that will
delete tasks older than 120 seconds for tasks that have been seen and
have a "final/completed" status like "skipped", "failed" or "done". To add
the `cleanup_tasks` periodic job to APS:

```python
from django.conf import settings
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from taskstate.tasks import cleanup_tasks


scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
scheduler.add_job(
    cleanup_tasks.send,
    trigger=CronTrigger(second='*/240'), # Every 240 seconds
    max_instances=1,
    replace_existing=True,
)
```




## Task statuses
- enqueued
- delayed
- running
- failed
- done
- skipped




## Get all completed tasks

```python
completed_tasks = Task.objects.completed()
```




## Get tasks for display
To get all the tasks that have been recently seen _and_ that have not been
seen (including currently active tasks), use the following:

```python
tasks = Task.objects.for_display()
```

This will show tasks that have been seen in the last 30 seconds. To only show
tasks seen in the last 15 seconds use the following:
```python
tasks = Task.objects.for_display(seconds_since_seen=15)
```




## Management commands
The `clear_tasks` management command will delete all `Task` objects currently
in the database irrespective of status.

```
python manage.py clear_tasks
```




## Compatibility
- Python 3.6+
- Django 3.2+
- Only supports PostgreSQL because `django.contrib.postgres.fields.ArrayField`
is used. This could be looked at in future.


## Versioning
This project follows [semantic versioning][200] (SemVer).


## License and code of conduct
Check the root of the repo for these files.








[//]: # (Links)

[1]: https://channels.readthedocs.io/en/stable/
[2]: https://channels.readthedocs.io/en/stable/topics/routing.html#urlrouter

[200]: https://semver.org/
