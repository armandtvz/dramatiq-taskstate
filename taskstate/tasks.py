import dramatiq

from taskstate.models import Task


@dramatiq.actor(max_retries=0)
def cleanup_tasks():
    Task.objects.delete_old(max_task_age=120)
    return
