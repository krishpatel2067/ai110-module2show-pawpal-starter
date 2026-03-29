from __future__ import annotations
import json
import os
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

    def remove_task(self, name: str, task_date: date = None) -> None:
        """Remove a task by name (and optionally date)."""
        if task_date is not None:
            if not any(t.name == name and t.date == task_date for t in self.tasks):
                raise ValueError(f"Task '{name}' on {task_date} not found.")
            self.tasks = [t for t in self.tasks if not (t.name == name and t.date == task_date)]
        else:
            if not any(t.name == name for t in self.tasks):
                raise ValueError(f"Task '{name}' not found.")
            self.tasks = [t for t in self.tasks if t.name != name]

    def remove_pet_from_tasks(self, pet_name: str) -> None:
        """Scrub a pet name from all tasks. Called by Owner.remove_pet."""
        for t in self.tasks:
            t.pet_names = [n for n in t.pet_names if n != pet_name]

    def get_tasks_for_pet(self, pet_name: str, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks assigned to a specific pet."""
        src = tasks if tasks is not None else self.tasks
        return [t for t in src if pet_name in t.pet_names]

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

    def get_tasks_sorted(self, sort_keys: list[str], tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks sorted by an ordered list of keys: 'Priority' and/or 'Date & Time'.
        Keys are applied left-to-right, so the first key is the primary sort."""
        src = tasks if tasks is not None else self.tasks

        def make_key(t: Task) -> tuple:
            parts: list = []
            for key in sort_keys:
                if key == "Priority":
                    parts.append(t.priority.value)
                elif key == "Date & Time":
                    parts.append(t.date)
                    parts.append(t.time_start or time.max)
            return tuple(parts)

        return sorted(src, key=make_key)

    def suggest_next_slot(
        self,
        duration_minutes: int,
        pet_name: str | None = None,
        starting_from: date | None = None,
    ) -> tuple[date, time] | None:
        """Return the earliest (date, time) where a task of duration_minutes fits
        without conflicting with existing scheduled tasks for pet_name.
        Searches up to 30 days forward from starting_from (default: today).
        If pet_name is None, checks against all scheduled tasks."""
        DAY_START = 8 * 60   # 08:00
        DAY_END = 22 * 60    # 22:00
        search_date = starting_from or date.today()

        for _ in range(30):
            base = self.get_tasks_for_pet(pet_name) if pet_name else list(self.tasks)
            day_tasks = sorted(
                [t for t in base if t.date == search_date and t.time_start and t.duration_minutes > 0],
                key=lambda t: t.time_start.hour * 60 + t.time_start.minute,
            )
            candidate_m = DAY_START
            for task in day_tasks:
                task_start_m = task.time_start.hour * 60 + task.time_start.minute
                if candidate_m + duration_minutes <= task_start_m:
                    return search_date, time(candidate_m // 60, candidate_m % 60)
                task_end_m = task_start_m + task.duration_minutes
                if task_end_m > candidate_m:
                    candidate_m = task_end_m
            if candidate_m + duration_minutes <= DAY_END:
                return search_date, time(candidate_m // 60, candidate_m % 60)
            search_date += timedelta(days=1)

        return None

    def get_conflicts(self, task: Task) -> list[Task]:
        """Return existing tasks whose time window overlaps with the given task.
        Only tasks sharing at least one pet on the same date are checked.
        Tasks without a time_start, duration, or pet are skipped."""
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
            # Only flag conflicts between tasks that share at least one pet
            if not task.pet_names or not existing.pet_names:
                continue
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

    def mark_complete(self, task_name: str, task_date: date = None) -> None:
        """Mark a task as completed and schedule the next occurrence if recurring."""
        for t in self.tasks:
            if t.name == task_name and not t.completed and (task_date is None or t.date == task_date):
                t.completed = True
                next_d = self._next_date(t.date, t.frequency)
                if next_d is not None:
                    self.tasks.append(replace(t, date=next_d, completed=False))
                return
        raise ValueError(f"Task '{task_name}' not found.")


# ── Persistence ──────────────────────────────────────────────────────────────

def _task_to_dict(t: Task) -> dict:
    return {
        "name": t.name,
        "description": t.description,
        "completed": t.completed,
        "frequency": t.frequency.value,
        "date": t.date.isoformat(),
        "priority": t.priority.name,
        "pet_names": t.pet_names,
        "time_start": t.time_start.strftime("%H:%M") if t.time_start else None,
        "duration_minutes": t.duration_minutes,
    }


def _task_from_dict(d: dict) -> Task:
    return Task(
        name=d["name"],
        description=d["description"],
        completed=d["completed"],
        frequency=Frequency(d["frequency"]),
        date=date.fromisoformat(d["date"]),
        priority=Priority[d["priority"]],
        pet_names=d["pet_names"],
        time_start=time.fromisoformat(d["time_start"]) if d["time_start"] else None,
        duration_minutes=d["duration_minutes"],
    )


def save_data(scheduler: Scheduler, path: str) -> None:
    """Serialize the owner and all tasks to a JSON file."""
    data = {
        "owner": {
            "name": scheduler.owner.name,
            "pets": [
                {"name": p.name, "species": p.species, "age_years": p.age_years, "notes": p.notes}
                for p in scheduler.owner.pets
            ],
        },
        "tasks": [_task_to_dict(t) for t in scheduler.tasks],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def delete_data(path: str) -> None:
    """Delete the saved data file if it exists."""
    if os.path.exists(path):
        os.remove(path)


def load_data(path: str) -> Scheduler | None:
    """Load owner and tasks from a JSON file. Returns None if the file doesn't exist."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    owner = Owner(name=data["owner"]["name"])
    for p in data["owner"]["pets"]:
        owner.pets.append(Pet(**p))
    scheduler = Scheduler(owner=owner)
    scheduler.tasks = [_task_from_dict(t) for t in data["tasks"]]
    return scheduler
