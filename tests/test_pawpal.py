import pytest
from datetime import date, time
from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task


@pytest.fixture
def scheduler():
    owner = Owner(name="Alex")
    owner.add_pet(Pet(name="Mochi", species="Cat", age_years=3.0))
    owner.add_pet(Pet(name="Rex", species="Dog", age_years=5.0))
    return Scheduler(owner=owner)


def make_task(name, d=None, priority=Priority.MEDIUM, frequency=Frequency.DAILY,
              pet_names=None, time_start=None, duration_minutes=0):
    return Task(
        name=name,
        description="",
        completed=False,
        frequency=frequency,
        date=d or date.today(),
        priority=priority,
        pet_names=pet_names or [],
        time_start=time_start,
        duration_minutes=duration_minutes,
    )


# ── Existing tests (updated for Frequency enum) ─────────────────────────────

def test_mark_complete_changes_task_status(scheduler):
    scheduler.add_task(make_task("Morning Feed", pet_names=["Mochi"]))
    scheduler.mark_complete("Morning Feed")
    assert scheduler.tasks[0].completed is True


def test_add_task_increases_pet_task_count(scheduler):
    assert len(scheduler.get_tasks_for_pet("Mochi")) == 0
    scheduler.add_task(make_task("Morning Feed", pet_names=["Mochi"]))
    assert len(scheduler.get_tasks_for_pet("Mochi")) == 1
    scheduler.add_task(make_task("Evening Feed", pet_names=["Mochi"]))
    assert len(scheduler.get_tasks_for_pet("Mochi")) == 2


# ── Sorting ──────────────────────────────────────────────────────────────────

def test_sort_by_priority(scheduler):
    scheduler.add_task(make_task("Low Task", priority=Priority.LOW))
    scheduler.add_task(make_task("High Task", priority=Priority.HIGH))
    scheduler.add_task(make_task("Medium Task", priority=Priority.MEDIUM))
    tasks = scheduler.get_tasks_sorted(["Priority"])
    assert [t.priority for t in tasks] == [Priority.HIGH, Priority.MEDIUM, Priority.LOW]


def test_sort_by_datetime_orders_by_date_then_time(scheduler):
    later_date = date(2026, 4, 2)
    earlier_date = date(2026, 4, 1)
    scheduler.add_task(make_task("Late Task", d=later_date, time_start=time(9, 0), duration_minutes=30))
    scheduler.add_task(make_task("Early Task", d=earlier_date, time_start=time(10, 0), duration_minutes=30))
    tasks = scheduler.get_tasks_sorted(["Date & Time"])
    assert tasks[0].name == "Early Task"
    assert tasks[1].name == "Late Task"


def test_sort_by_datetime_same_date_orders_by_time(scheduler):
    d = date(2026, 4, 1)
    scheduler.add_task(make_task("Afternoon", d=d, time_start=time(14, 0), duration_minutes=30))
    scheduler.add_task(make_task("Morning", d=d, time_start=time(8, 0), duration_minutes=30))
    tasks = scheduler.get_tasks_sorted(["Date & Time"])
    assert tasks[0].name == "Morning"
    assert tasks[1].name == "Afternoon"


def test_sort_by_datetime_untimed_tasks_sort_last(scheduler):
    d = date(2026, 4, 1)
    scheduler.add_task(make_task("No Time", d=d))
    scheduler.add_task(make_task("Has Time", d=d, time_start=time(8, 0), duration_minutes=30))
    tasks = scheduler.get_tasks_sorted(["Date & Time"])
    assert tasks[0].name == "Has Time"
    assert tasks[1].name == "No Time"


# ── Recurring task auto-creation ─────────────────────────────────────────────

def test_completing_daily_task_creates_next_day(scheduler):
    d = date(2026, 4, 1)
    scheduler.add_task(make_task("Feed", d=d, frequency=Frequency.DAILY, pet_names=["Mochi"]))
    scheduler.mark_complete("Feed")
    dates = [t.date for t in scheduler.tasks]
    assert date(2026, 4, 2) in dates


def test_completing_weekly_task_creates_next_week(scheduler):
    d = date(2026, 4, 1)
    scheduler.add_task(make_task("Bath", d=d, frequency=Frequency.WEEKLY, pet_names=["Mochi"]))
    scheduler.mark_complete("Bath")
    dates = [t.date for t in scheduler.tasks]
    assert date(2026, 4, 8) in dates


def test_completing_monthly_task_creates_next_month(scheduler):
    d = date(2026, 1, 31)
    scheduler.add_task(make_task("Vet", d=d, frequency=Frequency.MONTHLY, pet_names=["Mochi"]))
    scheduler.mark_complete("Vet")
    dates = [t.date for t in scheduler.tasks]
    assert date(2026, 2, 28) in dates  # Jan 31 + 1 month = Feb 28


def test_completing_yearly_task_creates_next_year(scheduler):
    d = date(2026, 3, 15)
    scheduler.add_task(make_task("Annual Checkup", d=d, frequency=Frequency.YEARLY, pet_names=["Mochi"]))
    scheduler.mark_complete("Annual Checkup")
    dates = [t.date for t in scheduler.tasks]
    assert date(2027, 3, 15) in dates


def test_completing_once_task_creates_no_next(scheduler):
    scheduler.add_task(make_task("Microchip", frequency=Frequency.ONCE, pet_names=["Mochi"]))
    scheduler.mark_complete("Microchip")
    assert len(scheduler.tasks) == 1


def test_recurring_next_task_is_incomplete(scheduler):
    d = date(2026, 4, 1)
    scheduler.add_task(make_task("Feed", d=d, frequency=Frequency.DAILY, pet_names=["Mochi"]))
    scheduler.mark_complete("Feed")
    next_task = next(t for t in scheduler.tasks if t.date == date(2026, 4, 2))
    assert next_task.completed is False


# ── Filtering ────────────────────────────────────────────────────────────────

def test_filter_by_pet(scheduler):
    scheduler.add_task(make_task("Mochi Task", pet_names=["Mochi"]))
    scheduler.add_task(make_task("Rex Task", pet_names=["Rex"]))
    tasks = scheduler.get_tasks_for_pet("Mochi")
    assert len(tasks) == 1
    assert tasks[0].name == "Mochi Task"


def test_filter_unassigned(scheduler):
    scheduler.add_task(make_task("Assigned", pet_names=["Mochi"]))
    scheduler.add_task(make_task("Unassigned"))
    tasks = scheduler.get_unassigned_tasks()
    assert len(tasks) == 1
    assert tasks[0].name == "Unassigned"


def test_filter_completed(scheduler):
    scheduler.add_task(make_task("Done", pet_names=["Mochi"]))
    scheduler.add_task(make_task("Pending", pet_names=["Mochi"]))
    scheduler.mark_complete("Done")
    tasks = scheduler.get_completed_tasks()
    assert all(t.completed for t in tasks)
    assert any(t.name == "Done" for t in tasks)


def test_filter_incomplete(scheduler):
    scheduler.add_task(make_task("Done", pet_names=["Mochi"]))
    scheduler.add_task(make_task("Pending", pet_names=["Mochi"]))
    scheduler.mark_complete("Done")
    tasks = scheduler.get_incomplete_tasks()
    assert all(not t.completed for t in tasks)
    assert any(t.name == "Pending" for t in tasks)


def test_filter_stacking_pet_then_completed(scheduler):
    scheduler.add_task(make_task("Mochi Done", pet_names=["Mochi"]))
    scheduler.add_task(make_task("Mochi Pending", pet_names=["Mochi"]))
    scheduler.add_task(make_task("Rex Done", pet_names=["Rex"]))
    scheduler.mark_complete("Mochi Done")
    scheduler.mark_complete("Rex Done")
    tasks = scheduler.get_completed_tasks(scheduler.get_tasks_for_pet("Mochi"))
    assert len(tasks) == 1
    assert tasks[0].name == "Mochi Done"


def test_filter_stacking_pet_then_incomplete(scheduler):
    scheduler.add_task(make_task("Mochi Done", pet_names=["Mochi"], frequency=Frequency.ONCE))
    scheduler.add_task(make_task("Mochi Pending", pet_names=["Mochi"]))
    scheduler.add_task(make_task("Rex Pending", pet_names=["Rex"]))
    scheduler.mark_complete("Mochi Done")
    tasks = scheduler.get_incomplete_tasks(scheduler.get_tasks_for_pet("Mochi"))
    assert len(tasks) == 1
    assert tasks[0].name == "Mochi Pending"


# ── Conflict detection ───────────────────────────────────────────────────────

def test_overlapping_tasks_same_pet_detected(scheduler):
    d = date(2026, 4, 1)
    scheduler.add_task(make_task("Walk", d=d, pet_names=["Mochi"],
                                 time_start=time(9, 0), duration_minutes=60))
    new_task = make_task("Groom", d=d, pet_names=["Mochi"],
                         time_start=time(9, 30), duration_minutes=30)
    assert len(scheduler.get_conflicts(new_task)) == 1


def test_adjacent_tasks_no_conflict(scheduler):
    d = date(2026, 4, 1)
    scheduler.add_task(make_task("Walk", d=d, pet_names=["Mochi"],
                                 time_start=time(9, 0), duration_minutes=60))
    new_task = make_task("Feed", d=d, pet_names=["Mochi"],
                         time_start=time(10, 0), duration_minutes=30)
    assert scheduler.get_conflicts(new_task) == []


def test_overlapping_tasks_different_pets_no_conflict(scheduler):
    d = date(2026, 4, 1)
    scheduler.add_task(make_task("Walk Mochi", d=d, pet_names=["Mochi"],
                                 time_start=time(9, 0), duration_minutes=60))
    new_task = make_task("Walk Rex", d=d, pet_names=["Rex"],
                         time_start=time(9, 30), duration_minutes=30)
    assert scheduler.get_conflicts(new_task) == []


def test_overlapping_tasks_different_dates_no_conflict(scheduler):
    scheduler.add_task(make_task("Walk", d=date(2026, 4, 1), pet_names=["Mochi"],
                                 time_start=time(9, 0), duration_minutes=60))
    new_task = make_task("Walk", d=date(2026, 4, 2), pet_names=["Mochi"],
                         time_start=time(9, 0), duration_minutes=60)
    assert scheduler.get_conflicts(new_task) == []


def test_task_without_time_no_conflict(scheduler):
    d = date(2026, 4, 1)
    scheduler.add_task(make_task("Walk", d=d, pet_names=["Mochi"],
                                 time_start=time(9, 0), duration_minutes=60))
    new_task = make_task("Feed", d=d, pet_names=["Mochi"])  # no time set
    assert scheduler.get_conflicts(new_task) == []
