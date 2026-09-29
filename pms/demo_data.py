from __future__ import annotations

import frappe
from frappe.utils import add_days, nowdate

from pms.api import _create_assignment, _upsert_project_member


DEMO_PROJECT_NAMES = (
    "PMS Demo Project",
    "Pomas Mobile Launch",
    "Client Portal Rollout",
    "Operations Board Pilot",
)
OWNER_USER = "Administrator"
MEMBER_USER = "jeanpaulabougharib@gmail.com"


def replace_demo_data() -> dict:
    """Replace only the known PMS demo projects with a representative Pomas dataset."""
    missing_users = [
        user for user in (OWNER_USER, MEMBER_USER)
        if not frappe.db.get_value("User", user, "enabled")
    ]
    if missing_users:
        frappe.throw(f"Enable the demo users before seeding: {', '.join(missing_users)}")

    demo_projects = frappe.get_all(
        "Project",
        filters={"project_name": ["in", DEMO_PROJECT_NAMES]},
        pluck="name",
        ignore_permissions=True,
    )
    removed_tasks = []
    for project in demo_projects:
        task_names = frappe.get_all(
            "Task", filters={"project": project}, pluck="name", ignore_permissions=True
        )
        removed_tasks.extend(task_names)
        if task_names:
            todo_names = frappe.get_all(
                "ToDo",
                filters={"reference_type": "Task", "reference_name": ["in", task_names]},
                pluck="name",
                ignore_permissions=True,
            )
            for todo in todo_names:
                frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)
            for task in task_names:
                frappe.delete_doc("Task", task, force=True, ignore_permissions=True)
        frappe.delete_doc("Project", project, force=True, ignore_permissions=True)

    today = nowdate()
    project_specs = [
        {
            "project_name": "Pomas Mobile Launch",
            "priority": "High",
            "expected_start_date": add_days(today, -18),
            "expected_end_date": add_days(today, 24),
            "notes": "Android release board for the first Pomas mobile build.",
            "tasks": [
                ("Finalize Android navigation", "Completed", "High", -15, -9, 100, OWNER_USER, True),
                ("Connect mobile board API", "Completed", "Urgent", -12, -5, 100, MEMBER_USER, False),
                ("Polish task detail drawer", "Working", "High", -3, 4, 55, MEMBER_USER, False),
                ("Prepare Play Store screenshots", "Open", "Medium", 2, 10, 0, None, False),
                ("Release candidate sign-off", "Pending Review", "Urgent", 8, 18, 85, OWNER_USER, True),
            ],
        },
        {
            "project_name": "Client Portal Rollout",
            "priority": "Medium",
            "expected_start_date": add_days(today, -35),
            "expected_end_date": add_days(today, 14),
            "notes": "Client onboarding rollout used to test progress and due-date sorting.",
            "tasks": [
                ("Map client onboarding journey", "Completed", "Medium", -32, -25, 100, OWNER_USER, False),
                ("Import customer contacts", "Completed", "Low", -24, -18, 100, MEMBER_USER, False),
                ("Configure welcome checklist", "Completed", "High", -18, -12, 100, OWNER_USER, True),
                ("Review portal permissions", "Pending Review", "High", -5, 2, 80, MEMBER_USER, False),
                ("Schedule customer training", "Open", "Medium", 1, 9, 0, None, False),
            ],
        },
        {
            "project_name": "Operations Board Pilot",
            "priority": "Low",
            "expected_start_date": add_days(today, -10),
            "expected_end_date": add_days(today, 40),
            "notes": "Pilot board with several unassigned tasks for claim-flow testing.",
            "tasks": [
                ("Define weekly operations cadence", "Working", "Medium", -8, 3, 35, OWNER_USER, False),
                ("Document incident handoff", "Overdue", "High", -7, -1, 20, None, False),
                ("Create supplier review template", "Open", "Low", 3, 14, 0, None, False),
                ("Draft service health checklist", "Open", "Medium", 5, 20, 0, None, True),
                ("Pilot retrospective", "Open", "Low", 22, 35, 0, None, False),
            ],
        },
    ]

    created_projects = []
    created_tasks = []
    pending_assignments = []
    seed_token = frappe.generate_hash(length=6).upper()
    for project_index, spec in enumerate(project_specs, start=1):
        project = frappe.get_doc(
            {
                "doctype": "Project",
                "project_name": spec["project_name"],
                "status": "Open",
                "priority": spec["priority"],
                "expected_start_date": spec["expected_start_date"],
                "expected_end_date": spec["expected_end_date"],
                "percent_complete_method": "Task Completion",
                "notes": spec["notes"],
                "users": [
                    {"user": OWNER_USER, "welcome_email_sent": 1},
                    {"user": MEMBER_USER, "welcome_email_sent": 1},
                ],
            }
        ).insert(ignore_permissions=True)
        created_projects.append(project.name)
        _upsert_project_member(project.name, OWNER_USER, "Owner")
        _upsert_project_member(project.name, MEMBER_USER, "Member")

        for task_index, (subject, status, priority, start_offset, end_offset, progress, assignee, milestone) in enumerate(spec["tasks"], start=1):
            task = frappe.get_doc(
                {
                    "doctype": "Task",
                    "project": project.name,
                    "subject": subject,
                    "status": status,
                    "priority": priority,
                    "exp_start_date": add_days(today, start_offset),
                    "exp_end_date": add_days(today, end_offset),
                    "progress": progress,
                    "expected_time": 4 if priority in ("Low", "Medium") else 8,
                    "description": f"Demo task for {spec['project_name']}. Open it to test task details and assignment behavior.",
                    "is_milestone": milestone,
                }
            )
            task.name = f"POMAS-DEMO-{seed_token}-{project_index:02d}-{task_index:02d}"
            task.flags.name_set = True
            task.insert(ignore_permissions=True)
            if assignee:
                pending_assignments.append((task.name, assignee))
            created_tasks.append(task.name)

        frappe.get_doc("Project", project.name).update_project()

    frappe.db.commit()

    for task_name, assignee in pending_assignments:
        _create_assignment(frappe.get_doc("Task", task_name), assignee, OWNER_USER)

    frappe.db.commit()
    return {
        "removed_projects": demo_projects,
        "removed_tasks": removed_tasks,
        "created_projects": created_projects,
        "created_tasks": created_tasks,
    }
