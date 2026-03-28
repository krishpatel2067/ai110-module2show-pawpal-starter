from dataclasses import dataclass, field
from datetime import date


@dataclass
class Task:
    """A single pet care task (walk, feeding, medication, etc.)."""

    name: str
    description: str
    completed: bool
    frequency: str       # e.g. "daily", "weekly", "as needed"
    date: date
    pet_name: str        # name of the associated pet, "All", or "None"


@dataclass
class Pet:
    """A pet owned by the owner."""

    name: str
    species: str
    age_years: float
    notes: str = ""


@dataclass
class Owner:
    """The pet owner. Holds a list of pets and can filter tasks by pet."""

    name: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's list."""
        ...

    def remove_pet(self, name: str) -> None:
        """Remove a pet by name from the owner's list."""
        ...



@dataclass
class Scheduler:
    """Manages all tasks across pets. Supports filtering and status updates."""

    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to the scheduler."""
        ...

    def remove_task(self, name: str) -> None:
        """Remove a task by name from the scheduler."""
        ...

    def get_tasks_for_pet(self, pet_name: str) -> list[Task]:
        """Return all tasks assigned to a specific pet (or tagged 'All')."""
        ...

    def get_tasks_for_date(self, target_date: date) -> list[Task]:
        """Return all tasks scheduled for a given date."""
        ...

    def mark_complete(self, task_name: str) -> None:
        """Mark a task as completed by name."""
        ...
