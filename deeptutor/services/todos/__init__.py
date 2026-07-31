"""Personal todos service — JSON CRUD for todo items.

Integrates with the email monitor feature to store extracted assignments
and todos from the user's university (M365) inbox.
"""

from .models import TodoItem
from .service import TodoService, get_todo_service, todo_service

__all__ = [
    "TodoItem",
    "TodoService",
    "get_todo_service",
    "todo_service",
]
