---
name: Architecture Decisions
description: Class responsibilities, interface contracts, and naming conventions for PawPal+ (simplified 4-class design)
type: project
---

## Phase completed: Phase 2 (Python OOP Skeleton — simplified)

## Class Responsibilities

| Class | File | Role |
|---|---|---|
| `Task` | `pawpal_system.py` | Dataclass. One pet care activity: name, description, completed, frequency, date, pet_name |
| `Pet` | `pawpal_system.py` | Dataclass. Pet info: name, species, age_years, notes. Composed into Owner. |
| `Owner` | `pawpal_system.py` | Dataclass. Owner name + list of Pet. Methods: add_pet, remove_pet, get_tasks |
| `Scheduler` | `pawpal_system.py` | Dataclass. Holds all tasks. Methods: add_task, remove_task, get_tasks_for_pet, get_tasks_for_date, mark_complete |

## Task.pet_name Convention

- Set to the pet's name string to associate a task with a specific pet
- Set to `"All"` to apply the task to every pet
- Set to `"None"` for tasks not tied to any pet

## Interface Contracts

- `Owner.get_tasks(tasks: list[Task]) -> list[Task]` — filters a task list to those belonging to the owner's pets or tagged "All"
- `Scheduler.get_tasks_for_pet(pet_name: str) -> list[Task]` — returns tasks where task.pet_name == pet_name or "All"
- `Scheduler.get_tasks_for_date(target_date: date) -> list[Task]` — returns tasks where task.date == target_date
- `Scheduler.mark_complete(task_name: str) -> None` — sets task.completed = True by matching name

## Design Rationale

Simplified from the original 10-class design (enums, constraints, ScheduledTask, Schedule, SchedulerContext, ABC hierarchy) down to 4 plain dataclasses. This is a student assignment — clarity beats sophistication. No priority queue, no constraint system, no heapq.

## File Layout (current)

```
app.py                  # Streamlit UI only
pawpal_system.py        # All 4 classes: Task, Pet, Owner, Scheduler
uml_diagram.md          # Mermaid classDiagram — 4 classes only
```
