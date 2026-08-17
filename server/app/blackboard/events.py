"""Blackboard event bus and change event shape."""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class BlackboardChange:
    """One successful blackboard mutation.

    The event carries the applied entry as well as a compact summary. It is
    published only for control/observability subscribers; knowledge sources
    never subscribe to this bus.
    """

    goal_id: str
    entry_id: str
    kind: str
    status: str
    previous_status: str
    revision: int
    summary: str = ""
    entry: Any = None


Subscriber = Callable[[BlackboardChange], Awaitable[None] | None]


class BlackboardEventBus:
    """In-process event notification for blackboard state changes."""

    def __init__(self) -> None:
        self._subscribers: list[Subscriber] = []

    def subscribe(self, callback: Subscriber) -> Callable[[], None]:
        self._subscribers.append(callback)

        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return unsubscribe

    async def publish(self, changes: list[BlackboardChange]) -> None:
        for change in changes:
            for callback in list(self._subscribers):
                result = callback(change)
                if inspect.isawaitable(result):
                    await result
