"""Task graph and dispatch order (spec 18.6, 41)."""

from __future__ import annotations

from dataclasses import dataclass, field


class CyclicTaskGraph(ValueError):
    pass


@dataclass(frozen=True)
class Task:
    task_id: str
    phase: str
    depends_on: tuple[str, ...] = ()


@dataclass
class TaskGraph:
    tasks: dict[str, Task] = field(default_factory=dict)

    def add(self, task: Task) -> "TaskGraph":
        if task.task_id in self.tasks:
            raise ValueError(f"duplicate task: {task.task_id}")
        self.tasks[task.task_id] = task
        return self

    def validate(self) -> None:
        for task in self.tasks.values():
            for dependency in task.depends_on:
                if dependency not in self.tasks:
                    raise KeyError(f"{task.task_id} depends on unknown task {dependency}")
        self.topological_order()

    def ready(self, completed: set[str]) -> list[str]:
        """Tasks whose dependencies are all satisfied and that are not done."""
        return sorted(
            t.task_id
            for t in self.tasks.values()
            if t.task_id not in completed and set(t.depends_on) <= completed
        )

    def topological_order(self) -> list[str]:
        completed: set[str] = set()
        order: list[str] = []
        while len(order) < len(self.tasks):
            ready = self.ready(completed)
            if not ready:
                remaining = sorted(set(self.tasks) - completed)
                raise CyclicTaskGraph(f"task graph has a cycle among: {', '.join(remaining)}")
            for task_id in ready:
                order.append(task_id)
                completed.add(task_id)
        return order
