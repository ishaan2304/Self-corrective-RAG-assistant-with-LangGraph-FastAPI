# Background Tasks

FastAPI lets you define operations that should run after returning a
response, without making the client wait for them — useful for things
like sending a confirmation email or writing a log entry after an action.

```python
from fastapi import BackgroundTasks

def write_log(message: str):
    with open("log.txt", "a") as f:
        f.write(message)

@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(write_log, f"notification sent to {email}")
    return {"message": "Notification sent in the background"}
```

## How It Works

`BackgroundTasks` is injected like any other dependency. Calling
`add_task` queues a function (with its arguments) to run after the
response has already been sent to the client, so the perceived latency
of the endpoint is unaffected by the task's execution time.

## Background Tasks and Dependencies

Background tasks can also be added inside dependencies, not just inside
the path operation function itself, which is convenient when the logic
for what needs to run afterward lives alongside a shared dependency.

## When Not to Use Background Tasks

For very heavy background processing — CPU-intensive work, or tasks that
need retries, scheduling, or to survive a server restart — a dedicated
task queue like Celery or an external worker system is a better fit than
FastAPI's built-in `BackgroundTasks`, which runs in-process and does not
persist across restarts.
