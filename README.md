# dramatiq-taskstate
A middleware for Dramatiq (for Django) that keeps track of task state only when you need it to.


## Quickstart
1. Install dramatiq-taskstate via pip:
   ```
   pip install dramatiq-taskstate
   ```
   Or via the repo:
   ```
   pip install git+https://github.com/armandtvz/dramatiq-taskstate.git
   ```

1. Add `taskstate` to your `INSTALLED_APPS` in your project settings.py file:
   ```python
   INSTALLED_APPS = [
       'django_dramatiq',
       '...',
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

1. Each time the `Task` object is updated a `task_changed` signal is dispatched
   which can be handled like this:
   ```python
   from django.dispatch import receiver

   from taskstate.middleware import StateMiddleware
   from taskstate.signals import task_changed

   @receiver(task_changed, sender=StateMiddleware)
   def handle_task_changed(sender, task, **kwargs):
       pass
   ```




## Management commands
The `clear_tasks` management command will delete all `Task` objects currently
in the database irrespective of status.
```
python manage.py clear_tasks
```




## Compatibility
- Compatible with Python 3.8 and above.
- Compatible with Django 3.2 and above.


## Versioning
This project follows [semantic versioning][200] (SemVer).


## License and code of conduct
Check the root of the repo for these files.








[//]: # (Links)

[200]: https://semver.org/
