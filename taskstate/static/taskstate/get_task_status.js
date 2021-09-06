/**
 * @function - Does not retrieve tasks; this only checks tasks based on
 * what is already in the UI. Expects task "components" in the UI to each
 * have a `task-status` CSS class.
 */
(function()
{
    'use strict';
    // The task_set contains all the task id's that
    // we want to request statuses of
    const task_set = new Set();

    const ws = {};
    if (window.location.protocol == 'https:')
    {
        ws.scheme = 'wss://';
    }
    else
    {
        ws.scheme = 'ws://';
    }

    const tasks = document.querySelectorAll('.task-status');
    if (! tasks)
    {
        return;
    }

    let socket = undefined;
    let task_seen_socket = undefined;
    try
    {
        socket = new WebSocket(
            ws.scheme
            + window.location.host
            + '/ws/get-task-status/'
        );
    }
    catch (e)
    {
        // Either the user has no tasks (maybe only old tasks shown in UI)
        // or is not logged in
        return;
    }
    try
    {
        task_seen_socket = new WebSocket(
            ws.scheme
            + window.location.host
            + '/ws/set-task-seen/'
        );
    }
    catch (e)
    {
        // Either the user has no tasks (maybe only old tasks shown in UI)
        // or is not logged in
        return;
    }


    for (let i = 0; i < tasks.length; i++)
    {
        const task = tasks[i];
        const status = task.dataset.status;
        const pk = task.dataset.pk;
        if (! pk)
        {
            throw Error('ID (primary key) for task must be provided.');
        }

        if (status === 'running' || status === 'enqueued')
        {
            task.classList.add('active');
            task_set.add(pk);
        }
        else
        {
            task.classList.remove('active');
            task_set.delete(pk);
        }
    }

    function send_payload(_socket)
    {
        const payload = JSON.stringify({
            'pk_list': Array.from(task_set),
        });
        _socket.send(payload);
    }

    task_seen_socket.onopen = (event) =>
    {
        send_payload(task_seen_socket);
    }


    socket.onopen = (event) =>
    {
        send_payload(socket);
    }

    socket.onmessage = (event) =>
    {
        const response = JSON.parse(event.data);
        const tasks_returned = response.tasks;

        for (let i = 0; i < tasks_returned.length; i++)
        {
            const task = tasks_returned[i];
            const pk = task.pk;
            const status = task.status;

            const selector = '.task-status[data-pk="' + pk.toString() + '"]';
            const task_element = document.querySelector(selector);
            const task_status = task_element.querySelector('.task-status-text');
            if (status === 'done' || status === 'failed' || status === 'skipped')
            {
                task_element.classList.remove('active');
                // Let the server know that these tasks have been seen after
                // completing. The server will automatically set all tasks to
                // the correct seen status.
                send_payload(task_seen_socket);
            }
            task_status.textContent = status;
            task_element.dataset.status = status;

            if (task.progress)
            {
                const progress = task_element.querySelector('.progress');
                if (progress)
                {
                    progress.textContent = task.progress + '%';
                }
            }
        }
    }
}());
