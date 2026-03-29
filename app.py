import streamlit as st
from datetime import date, time
from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ── Session state initialization ────────────────────

if "owner" not in st.session_state:
    st.session_state.owner = None
if "scheduler" not in st.session_state:
    st.session_state.scheduler = None
if "task_form_version" not in st.session_state:
    st.session_state.task_form_version = 0
if "pet_form_version" not in st.session_state:
    st.session_state.pet_form_version = 0
if "filter_pet" not in st.session_state:
    st.session_state.filter_pet = "All"
if "filter_status" not in st.session_state:
    st.session_state.filter_status = "All"
if "sort_by" not in st.session_state:
    st.session_state.sort_by = "Priority"

# ── Section 1: Owner Setup ──────────────────────────

st.header("Owner Setup")

owner_name = st.text_input("Your name", placeholder="e.g. Alex")

if st.button("Create Owner"):
    if not owner_name.strip():
        st.error("Please enter a name.")
    else:
        st.session_state.owner = Owner(name=owner_name.strip())
        st.session_state.scheduler = Scheduler(owner=st.session_state.owner)
        st.success(f"Welcome, {owner_name.strip()}!")

if st.session_state.owner:
    st.caption(f"Current owner: **{st.session_state.owner.name}**")

# ── Section 2: Manage Pets ──────────────────────────

if st.session_state.owner:
    st.divider()
    st.header("Manage Pets")

    with st.form(f"add_pet_form_{st.session_state.pet_form_version}"):
        col1, col2, col3 = st.columns(3)
        with col1:
            pet_name = st.text_input("Name")
        with col2:
            species = st.text_input("Species", placeholder="e.g. Cat, Dog")
        with col3:
            age = st.number_input("Age (years)", min_value=0.0, step=0.5)
        notes = st.text_input("Notes", placeholder="e.g. Allergic to chicken")
        submitted = st.form_submit_button("Add Pet")

    if submitted:
        if not pet_name.strip() or not species.strip():
            st.error("Name and species are required.")
        else:
            try:
                st.session_state.owner.add_pet(
                    Pet(
                        name=pet_name.strip(),
                        species=species.strip(),
                        age_years=age,
                        notes=notes.strip(),
                    )
                )
                st.success(f"Added {pet_name.strip()}!")
                st.session_state.pet_form_version += 1
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    pets = st.session_state.owner.pets
    if not pets:
        st.info("No pets yet. Add one above.")
    else:
        for pet in pets:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(
                    f"**{pet.name}** — {pet.species}, {pet.age_years}y"
                    + (f" _{pet.notes}_" if pet.notes else "")
                )
            with col2:
                if st.button("🗑️", key=f"remove_pet_{pet.name}"):
                    try:
                        st.session_state.owner.remove_pet(
                            pet.name, st.session_state.scheduler
                        )
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

# ── Section 3: Tasks ────────────────────────────────

if st.session_state.owner:
    st.divider()
    st.header("Tasks")

    pet_names = [p.name for p in st.session_state.owner.pets]

    with st.form(f"add_task_form_{st.session_state.task_form_version}"):
        col1, col2 = st.columns(2)
        with col1:
            task_name = st.text_input("Task name")
            frequency = st.selectbox("Frequency", [""] + [f.value for f in Frequency])
            priority = st.selectbox("Priority", [""] + [p.name for p in Priority])
        with col2:
            description = st.text_input("Description")
            task_date = st.date_input("Date", value=date.today())
            assigned_pets = st.multiselect("Assign to pets", pet_names)
        col3, col4 = st.columns(2)
        with col3:
            time_start = st.time_input("Start time", value=None)
        with col4:
            duration_minutes = st.number_input("Duration (min)", min_value=0, step=15, value=0)
        submitted = st.form_submit_button("Add Task")

    if submitted:
        if not task_name.strip() or not frequency or not priority:
            st.error("Task name, frequency, and priority are required.")
        elif time_start is not None and duration_minutes == 0:
            st.error("Please set a duration when specifying a start time.")
        else:
            try:
                new_task = Task(
                    name=task_name.strip(),
                    description=description.strip(),
                    completed=False,
                    frequency=Frequency(frequency),
                    date=task_date,
                    priority=Priority[priority],
                    pet_names=assigned_pets,
                    time_start=time_start if duration_minutes > 0 else None,
                    duration_minutes=duration_minutes,
                )
                st.session_state.scheduler.add_task(new_task)
                st.success(f"Added task '{task_name.strip()}'!")
                st.session_state.task_form_version += 1
                st.session_state.filter_pet = "All"
                st.session_state.filter_status = "All"
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    st.subheader("Schedule")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox("Filter by pet", ["All", "None"] + pet_names, key="filter_pet")
    with col2:
        st.selectbox("Filter by status", ["All", "Incomplete", "Completed"], key="filter_status")
    with col3:
        st.selectbox("Sort by", ["Priority", "Date & Time"], key="sort_by")

    scheduler = st.session_state.scheduler
    active_pet = st.session_state.get("filter_pet", "All")
    active_status = st.session_state.get("filter_status", "All")
    sort_by = st.session_state.get("sort_by", "Priority")

    # Stack filters then sort
    tasks = None
    if active_pet == "None":
        tasks = scheduler.get_unassigned_tasks()
    elif active_pet != "All":
        tasks = scheduler.get_tasks_for_pet(active_pet)

    if active_status == "Completed":
        tasks = scheduler.get_completed_tasks(tasks)
    elif active_status == "Incomplete":
        tasks = scheduler.get_incomplete_tasks(tasks)

    if sort_by == "Date & Time":
        tasks = scheduler.get_tasks_by_datetime(tasks)
    else:
        tasks = scheduler.get_tasks_by_priority(tasks)

    if not tasks:
        st.info("No tasks match the current filter.")
    else:
        conflicted = {t.name for t in tasks if scheduler.get_conflicts(t)}
        for task in tasks:
            with st.container(border=True):
                col_main, col_complete, col_delete = st.columns([6, 1, 1])
                with col_main:
                    status = "✓" if task.completed else "○"
                    date_label = task.date.strftime("%b %d, %Y")
                    time_label = ""
                    if task.time_start:
                        time_label = f" · {task.time_start.strftime('%H:%M')}"
                        if task.duration_minutes > 0:
                            end = time(
                                (task.time_start.hour * 60 + task.time_start.minute + task.duration_minutes) // 60 % 24,
                                (task.time_start.minute + task.duration_minutes) % 60,
                            )
                            time_label += f"–{end.strftime('%H:%M')} ({task.duration_minutes} min)"
                    conflict_flag = " ⚠️" if task.name in conflicted else ""
                    st.markdown(f"**{status} {task.name}**{conflict_flag} &nbsp; {date_label}{time_label}")
                    pets_label = ", ".join(task.pet_names) if task.pet_names else "No pets"
                    st.caption(f"{task.priority.name} · {task.frequency.value} · {pets_label}")
                    if task.description:
                        st.caption(f"_{task.description}_")
                with col_complete:
                    if not task.completed:
                        if st.button("✅", key=f"complete_{task.name}"):
                            st.session_state.scheduler.mark_complete(task.name)
                            st.rerun()
                with col_delete:
                    if st.button("🗑️", key=f"remove_task_{task.name}"):
                        try:
                            st.session_state.scheduler.remove_task(task.name)
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

