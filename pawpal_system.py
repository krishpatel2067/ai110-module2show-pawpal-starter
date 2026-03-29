from __future__ import annotations
from dataclasses import dataclass, field, replace
from dateutil.relativedelta import relativedelta
from datetime import date, time, timedelta
from enum import Enum


class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class Frequency(Enum):
    ONCE = "Once"
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    YEARLY = "Yearly"


@dataclass
class Task:
    """A single pet care task (walk, feeding, medication, etc.)."""

    name: str
    description: str
    completed: bool
    frequency: Frequency
    date: date
    priority: Priority
    pet_names: list[str] = field(default_factory=list)  # empty = no pets assigned
    time_start: time | None = None
    duration_minutes: int = 0

    def __post_init__(self) -> None:
        """Remove duplicate pet names while preserving their original order."""
        self.pet_names = list(dict.fromkeys(self.pet_names))


@dataclass
class Pet:
    """A pet owned by the owner."""

    name: str
    species: str
    age_years: float
    notes: str = ""


@dataclass
class Owner:
    """The pet owner. Holds a list of pets."""

    name: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's list."""
        if any(p.name == pet.name for p in self.pets):
            raise ValueError(f"Pet '{pet.name}' already exists.")
        self.pets.append(pet)

    def remove_pet(self, name: str, scheduler: Scheduler) -> None:
        """Remove a pet by name and scrub it from all tasks in the scheduler."""
        if not any(p.name == name for p in self.pets):
            raise ValueError(f"Pet '{name}' not found.")
        self.pets = [p for p in self.pets if p.name != name]
        scheduler.remove_pet_from_tasks(name)


@dataclass
class Scheduler:
    """Manages all tasks for an owner across their pets."""

    owner: Owner
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task. Validates all pet_names exist. Merges pet_names if task name already exists."""
        unknown = [n for n in task.pet_names if not any(p.name == n for p in self.owner.pets)]
        if unknown:
            raise ValueError(f"Unknown pet(s): {', '.join(unknown)}. Add them to the owner first.")
        for existing in self.tasks:
            if existing.name == task.name and existing.date == task.date:
                existing.pet_names = list(dict.fromkeys(existing.pet_names + task.pet_names))
                return
        self.tasks.append(task)

    def remove_task(self, name: str) -> None:
        """Remove a task by name."""
        if not any(t.name == name for t in self.tasks):
            raise ValueError(f"Task '{name}' not found.")
        self.tasks = [t for t in self.tasks if t.name != name]

    def remove_pet_from_tasks(self, pet_name: str) -> None:
        """Scrub a pet name from all tasks. Called by Owner.remove_pet."""
        for t in self.tasks:
            t.pet_names = [n for n in t.pet_names if n != pet_name]

    def task_count_for_pet(self, pet_name: str) -> int:
        """Return the number of tasks assigned to a specific pet."""
        return len(self.get_tasks_for_pet(pet_name))

    def get_tasks_for_pet(self, pet_name: str, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks assigned to a specific pet."""
        src = tasks if tasks is not None else self.tasks
        return [t for t in src if pet_name in t.pet_names]

    def get_tasks_for_date(self, target_date: date, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks scheduled for a given date."""
        src = tasks if tasks is not None else self.tasks
        return [t for t in src if t.date == target_date]

    def get_unassigned_tasks(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks with no pets assigned."""
        src = tasks if tasks is not None else self.tasks
        return [t for t in src if not t.pet_names]

    def get_completed_tasks(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return completed tasks."""
        src = tasks if tasks is not None else self.tasks
        return [t for t in src if t.completed]

    def get_incomplete_tasks(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return incomplete tasks."""
        src = tasks if tasks is not None else self.tasks
        return [t for t in src if not t.completed]

    def get_tasks_by_priority(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks sorted HIGH to LOW priority."""
        src = tasks if tasks is not None else self.tasks
        return sorted(src, key=lambda t: t.priority.value)

    def get_tasks_by_datetime(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks sorted by date then start time (untimed tasks sort last within a day)."""
        src = tasks if tasks is not None else self.tasks
        return sorted(src, key=lambda t: (t.date, t.time_start or time.max))

    def get_conflicts(self, task: Task) -> list[Task]:
        """Return existing tasks whose time window overlaps with the given task.
        Only tasks sharing at least one pet (or both unassigned) on the same date are checked.
        Tasks without a time_start or duration are skipped."""
        if task.time_start is None or task.duration_minutes <= 0:
            return []

        def to_minutes(t: time) -> int:
            return t.hour * 60 + t.minute

        task_start = to_minutes(task.time_start)
        task_end = task_start + task.duration_minutes
        conflicts = []

        for existing in self.tasks:
            if existing.name == task.name:
                continue
            if existing.date != task.date:
                continue
            if existing.time_start is None or existing.duration_minutes <= 0:
                continue
            # Only flag conflicts between tasks that share a pet (or are both unassigned)
            if task.pet_names and existing.pet_names:
                if not set(task.pet_names) & set(existing.pet_names):
                    continue
            existing_start = to_minutes(existing.time_start)
            existing_end = existing_start + existing.duration_minutes
            if task_start < existing_end and existing_start < task_end:
                conflicts.append(existing)

        return conflicts

    def _next_date(self, d: date, freq: Frequency) -> date | None:
        """Return the next occurrence date for a given frequency, or None for ONCE."""
        if freq == Frequency.ONCE:
            return None
        if freq == Frequency.DAILY:
            return d + timedelta(days=1)
        if freq == Frequency.WEEKLY:
            return d + timedelta(weeks=1)
        if freq == Frequency.MONTHLY:
            return d + relativedelta(months=1)
        # YEARLY
        return d + relativedelta(years=1)

    def mark_complete(self, task_name: str) -> None:
        """Mark a task as completed and schedule the next occurrence if recurring."""
        for t in self.tasks:
            if t.name == task_name and not t.completed:
                t.completed = True
                next_d = self._next_date(t.date, t.frequency)
                if next_d is not None:
                    self.tasks.append(replace(t, date=next_d, completed=False))
                return
        raise ValueError(f"Task '{task_name}' not found.")
