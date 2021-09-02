import dramatiq

from taskstate.models import Task


@dramatiq.actor(max_retries=0)
def cleanup_tasks():
    Task.objects.delete_old_tasks(max_task_age=30)
    return
