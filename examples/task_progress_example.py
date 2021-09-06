import math

import dramatiq
from dramatiq.middleware import CurrentMessage


def update_task_progress(current, total, task):
    """
    Return True if updated
    Return False if not.
    """
    if total >= 50:
        progress = (current / total) * 100
        progress = math.ceil(progress)
        if progress % 10 == 0:
            task.progress = progress
            task.save()
            return True
    return False


@dramatiq.actor(max_retries=0)
def progress_task(arg, for_state={}):
    # Make sure to use dramatiq.middleware.CurrentMessage in
    # your Dramatiq middleware otherwise this won't work.
    # We need the message to lookup the task.
    # https://dramatiq.io/reference.html#dramatiq.middleware.CurrentMessage
    message = CurrentMessage.get_current_message()
    task = None
    try:
        task = Task.objects.get(message_id=message.message_id)
    except Task.DoesNotExist:
        pass

    things = [
        'thing',
        'thing',
        'thing',
        'thing',
        'thing',
        'thing',
        'thing',
        'thing',
        'thing',
        'thing',
    ]
    total = len(things)
    current = 0

    for thing in things:
        current += 1
        if task:
            update_task_progress(current, total, task)
    return
