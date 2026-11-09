from typing import Any
from urllib.parse import quote

from playwright.sync_api import APIRequestContext, APIResponse


class TasksAPI:
    """Task endpoints; return raw responses so tests can assert success or errors."""

    path = "/api/tasks"

    def __init__(self, context: APIRequestContext):
        self.context = context

    def list(self) -> APIResponse:
        return self.context.get(self.path)

    def create(self, title: str) -> APIResponse:
        return self.create_payload({"title": title})

    def create_payload(self, payload: Any) -> APIResponse:
        return self.context.post(self.path, data=payload)

    def create_raw(self, body: bytes) -> APIResponse:
        return self.context.post(
            self.path, data=body, headers={"Content-Type": "application/json"}
        )

    def get(self, task_id: str) -> APIResponse:
        return self.context.get(self._task_path(task_id))

    def delete(self, task_id: str) -> APIResponse:
        return self.context.delete(self._task_path(task_id))

    def _task_path(self, task_id: str) -> str:
        return f"{self.path}/{quote(task_id, safe='')}"
