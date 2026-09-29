from __future__ import annotations

import json
import base64
import os
import time
from io import BytesIO
import jwt
import requests

import frappe
from frappe import _
import re
from urllib.parse import urlparse
from frappe.utils import escape_html, strip_html
from frappe.utils.file_manager import save_file
from PIL import Image, ImageOps


ADMIN_ROLES = {"System Manager", "PMS Administrator"}
GITHUB_API_URL = "https://api.github.com"
PROJECT_MANAGER_ROLES = ADMIN_ROLES | {"PMS Project Manager", "PMS Project Admin"}
GITHUB_REPOSITORY_URL_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
PMS_ROLES = PROJECT_MANAGER_ROLES | {"PMS User"}
BOARD_STATUSES = ("Open", "Working", "Pending Review", "Overdue", "Completed")
TASK_CREATE_STATUSES = ("Open",)
TASK_PRIORITIES = ("Low", "Medium", "High", "Urgent")
PRIORITY_RANK = {"Low": 1, "Medium": 2, "High": 3, "Urgent": 4}


def _require_user() -> str:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to use PMS."), frappe.AuthenticationError)
    return user


def _roles(user: str) -> set[str]:
    return set(frappe.get_roles(user))


def _is_administrator(user: str) -> bool:
    return user == "Administrator" or bool(_roles(user) & ADMIN_ROLES)


def _is_project_manager(user: str, roles: set[str] | None = None) -> bool:
    user_roles = roles if roles is not None else _roles(user)
    return user == "Administrator" or bool(user_roles & PROJECT_MANAGER_ROLES)


def _require_project_manager(user: str, roles: set[str] | None = None) -> None:
    # Legacy global-role guard retained for the GitHub system settings only.
    if not _is_project_manager(user, roles):
        frappe.throw(_("Only a project manager can perform this action."), frappe.PermissionError)


def _require_pms_access(user: str) -> set[str]:
    roles = _roles(user)
    if user != "Administrator" and not roles.intersection(PMS_ROLES):
        frappe.throw(_("Your account does not have PMS access."), frappe.PermissionError)
    return roles


def _member_project_names(user: str) -> set[str]:
    memberships = frappe.get_all(
        "Project User",
        filters={"user": user, "parenttype": "Project"},
        pluck="parent",
        ignore_permissions=True,
    )
    owned = frappe.get_all("Project", filters={"owner": user}, pluck="name", ignore_permissions=True)
    return set(memberships) | set(owned)


def _assert_project_access(project: str, user: str) -> None:
    if _is_administrator(user):
        return
    if project not in _member_project_names(user):
        frappe.throw(_("You do not have access to this project."), frappe.PermissionError)


PROJECT_MEMBER_ROLES = {"Owner", "Project Manager", "Member"}


def _project_role(project: str, user: str) -> str | None:
    """Return this user's authority in one Project, never a global Pomas role."""
    if _is_administrator(user):
        return "Owner"
    if frappe.db.get_value("Project", project, "owner") == user:
        return "Owner"
    role = frappe.db.get_value(
        "PMS Project Member", {"project": project, "user": user}, "project_role"
    )
    if role in PROJECT_MEMBER_ROLES:
        return role
    # Backward-compatible read access for Project User rows until every old Project is migrated.
    return "Member" if project in _member_project_names(user) else None


def _can_manage_project(project: str, user: str) -> bool:
    return _project_role(project, user) in {"Owner", "Project Manager"}


def _require_project_manager_for(project: str, user: str) -> None:
    if not _can_manage_project(project, user):
        frappe.throw(_("Only this Project's owner or project admin can perform this action."), frappe.PermissionError)


def _require_project_owner_for(project: str, user: str) -> None:
    if _project_role(project, user) != "Owner":
        frappe.throw(_("Only this Project's owner can manage its team and settings."), frappe.PermissionError)


def _upsert_project_member(project: str, member: str, project_role: str) -> None:
    name = frappe.db.get_value("PMS Project Member", {"project": project, "user": member}, "name")
    if name:
        frappe.db.set_value("PMS Project Member", name, "project_role", project_role, update_modified=True)
        return
    frappe.get_doc({"doctype": "PMS Project Member", "project": project, "user": member, "project_role": project_role}).insert(ignore_permissions=True)

def _decode_assignments(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return []


def _project_member_users(project: str) -> set[str]:
    users = set(
        frappe.get_all(
            "Project User",
            filters={"parent": project, "parenttype": "Project"},
            pluck="user",
            ignore_permissions=True,
        )
    )
    owner = frappe.db.get_value("Project", project, "owner")
    if owner:
        users.add(owner)
    return users


def _pomas_users() -> list[dict]:
    role_holders = set(
        frappe.get_all(
            "Has Role",
            filters={"parenttype": "User", "role": ["in", sorted(PMS_ROLES | {"System Manager"})]},
            pluck="parent",
            ignore_permissions=True,
        )
    )
    if not role_holders:
        return []
    return frappe.get_all(
        "User",
        filters={"name": ["in", sorted(role_holders)], "enabled": 1},
        fields=["name", "full_name", "user_image"],
        order_by="full_name asc",
        ignore_permissions=True,
    )


def _normalize_users(value: list[str] | str | None, legacy_user: str | None = None) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            value = []
    users = value if isinstance(value, list) else []
    if legacy_user:
        users = [*users, legacy_user]
    return list(dict.fromkeys(str(member).strip() for member in users if str(member).strip()))


def _validate_project_users(project: str, users: list[str]) -> None:
    if len(users) > 50:
        frappe.throw(_("A task can have at most 50 assignees."))
    member_users = _project_member_users(project)
    for member in users:
        if member not in member_users:
            frappe.throw(_("Tasks can only be assigned to a member of this project."), frappe.PermissionError)
        if not frappe.db.get_value("User", member, "enabled"):
            frappe.throw(_("The selected assignee is disabled."))


def _task_assignees(task: str) -> list[str]:
    return frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "Task",
            "reference_name": task,
            "status": ["!=", "Cancelled"],
        },
        pluck="allocated_to",
        order_by="creation asc",
        ignore_permissions=True,
    )



def _task_submissions(task: str) -> list[dict]:
    """Return submitted work metadata for a task already authorized by its caller."""
    submissions = frappe.get_all(
        "PMS Work Submission",
        filters={"task": task},
        fields=["name", "submitted_by", "submitted_on", "description"],
        order_by="submitted_on desc",
        limit_page_length=1,
        ignore_permissions=True,
    )
    for submission in submissions:
        submission["files"] = frappe.get_all(
            "PMS Work Submission File",
            filters={"parent": submission.name, "parenttype": "PMS Work Submission"},
            fields=["name", "file_name", "repository_path", "file", "file_size"],
            order_by="idx asc",
            ignore_permissions=True,
        )
    return submissions
def _task_payload(task: dict, project_name: str | None = None) -> dict:
    as_dict = getattr(task, "as_dict", None)
    task = as_dict() if callable(as_dict) else dict(task)
    task["assignees"] = _task_assignees(task["name"])
    task["description"] = strip_html(task.get("description") or "")
    task["submissions"] = _task_submissions(task["name"]) if task.get("status") in {"Pending Review", "Completed"} else []
    if project_name is not None:
        task["project_name"] = project_name
    can_manage = _can_manage_project(task.get("project"), frappe.session.user) if task.get("project") else False
    task["can_take"] = not task["assignees"] and task.get("status") in {"Open", "Overdue"}
    task["can_submit"] = frappe.session.user in task["assignees"] and task.get("status") in {"Working", "Overdue"}
    task["can_edit"] = can_manage and not task["assignees"] and task.get("status") == "Open"
    task["can_delete"] = task["can_edit"]
    task["can_review"] = can_manage and task.get("status") == "Pending Review"
    return task


def _sync_overdue_tasks(project: str | None = None) -> int:
    """Mark only dated active Tasks overdue and heal old undated false-overdue records."""
    scope = [["project", "=", project]] if project else []
    undated_overdue = frappe.get_all(
        "Task",
        filters=[["status", "=", "Overdue"], ["exp_end_date", "is", "not set"], *scope],
        fields=["name"],
        ignore_permissions=True,
    )
    for task in undated_overdue:
        restored_status = "Working" if _task_assignees(task.name) else "Open"
        frappe.db.set_value("Task", task.name, "status", restored_status, update_modified=True)

    dated_active_filters = [
        ["status", "in", ["Open", "Working"]],
        ["exp_end_date", "is", "set"],
        ["exp_end_date", "<", frappe.utils.nowdate()],
        *scope,
    ]
    late_tasks = frappe.get_all("Task", filters=dated_active_filters, fields=["name"], ignore_permissions=True)
    for late_task in late_tasks:
        frappe.db.set_value("Task", late_task.name, "status", "Overdue", update_modified=True)
    return len(late_tasks) + len(undated_overdue)

def _sync_due_priorities(project: str | None = None) -> int:
    """Escalate active Task priority as a real due date approaches; never lower it."""
    scope = [["project", "=", project]] if project else []
    tasks = frappe.get_all(
        "Task",
        filters=[
            ["status", "in", ["Open", "Working", "Overdue"]],
            ["exp_end_date", "is", "set"],
            *scope,
        ],
        fields=["name", "priority", "exp_end_date"],
        ignore_permissions=True,
    )
    updated = 0
    today = frappe.utils.nowdate()
    for task in tasks:
        days_remaining = frappe.utils.date_diff(task.exp_end_date, today)
        minimum = "Urgent" if days_remaining <= 0 else "High" if days_remaining <= 2 else "Medium" if days_remaining <= 7 else None
        if minimum and PRIORITY_RANK.get(task.priority, 0) < PRIORITY_RANK[minimum]:
            frappe.db.set_value("Task", task.name, "priority", minimum, update_modified=True)
            updated += 1
    return updated


def mark_overdue_tasks() -> int:
    """Hourly scheduler entry point for due-date status and priority escalation."""
    return _sync_overdue_tasks() + _sync_due_priorities()


def _create_assignment(task: dict, allocated_to: str, assigned_by: str) -> None:
    frappe.get_doc(
        {
            "doctype": "ToDo",
            "allocated_to": allocated_to,
            "reference_type": "Task",
            "reference_name": task.name,
            "description": task.description or task.subject,
            "priority": "High" if task.priority == "Urgent" else task.priority,
            "status": "Open",
            "date": task.exp_end_date or frappe.utils.nowdate(),
            "assigned_by": assigned_by,
        }
    ).insert(ignore_permissions=True)


@frappe.whitelist()
def get_task_form_options(project: str) -> dict:
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_manager_for(project, user)

    members = [
        member for member in _pomas_users()
        if member.name in _project_member_users(project)
    ]

    return {
        "statuses": list(TASK_CREATE_STATUSES),
        "priorities": list(TASK_PRIORITIES),
        "members": members,
    }



@frappe.whitelist()
def get_clients() -> list[dict]:
    """List standard ERPNext Customers for Pomas Project selection."""
    user = _require_user()
    _require_pms_access(user)
    return frappe.get_all("Customer", fields=["name", "customer_name"], order_by="customer_name asc", ignore_permissions=True)


@frappe.whitelist()
def create_client(
    customer_name: str,
    customer_type: str = "Organization",
    email: str | None = None,
    phone: str | None = None,
    address_line1: str | None = None,
    address_line2: str | None = None,
    city: str | None = None,
    country: str | None = None,
) -> dict:
    """Create a standard Customer with optional linked Contact and Address records."""
    user = _require_user()
    _require_pms_access(user)
    customer_name = (customer_name or "").strip()
    customer_type = (customer_type or "Organization").strip()
    email, phone = (email or "").strip(), (phone or "").strip()
    address_line1, address_line2 = (address_line1 or "").strip(), (address_line2 or "").strip()
    city, country = (city or "").strip(), (country or "").strip()
    if not customer_name:
        frappe.throw(_("Client name is required."), frappe.ValidationError)
    if len(customer_name) > 140:
        frappe.throw(_("Client name cannot exceed 140 characters."), frappe.ValidationError)
    if customer_type not in {"Organization", "Individual"}:
        frappe.throw(_("Choose Organization or Individual."), frappe.ValidationError)
    existing = frappe.db.get_value("Customer", {"customer_name": customer_name}, ["name", "customer_name"], as_dict=True)
    if existing:
        frappe.throw(_("A client with this name already exists. Select it from the list."), frappe.ValidationError)
    if email and not frappe.utils.validate_email_address(email, throw=False):
        frappe.throw(_("Enter a valid client email address."), frappe.ValidationError)
    has_address = any([address_line1, address_line2, city, country])
    if has_address and (not address_line1 or not city or not country):
        frappe.throw(_("Address line, city, and country are required when adding an address."), frappe.ValidationError)
    if country and not frappe.db.exists("Country", country):
        frappe.throw(_("Select a valid country."), frappe.ValidationError)

    customer = frappe.get_doc({"doctype": "Customer", "customer_name": customer_name, "customer_type": "Company" if customer_type == "Organization" else "Individual"})
    customer.insert(ignore_permissions=True)
    if email or phone:
        contact_data = {"doctype": "Contact", "first_name": customer_name, "links": [{"link_doctype": "Customer", "link_name": customer.name}]}
        if email:
            contact_data["email_ids"] = [{"email_id": email, "is_primary": 1}]
        if phone:
            contact_data["phone_nos"] = [{"phone": phone, "is_primary_phone": 1}]
        frappe.get_doc(contact_data).insert(ignore_permissions=True)
    if has_address:
        frappe.get_doc({"doctype": "Address", "address_title": customer_name, "address_type": "Billing", "address_line1": address_line1, "address_line2": address_line2 or None, "city": city, "country": country, "links": [{"link_doctype": "Customer", "link_name": customer.name}]}).insert(ignore_permissions=True)
    return {"name": customer.name, "customer_name": customer.customer_name}


@frappe.whitelist()
def get_project_member_options() -> list[dict]:
    user = _require_user()
    _require_pms_access(user)
    return [member for member in _pomas_users() if member.name != user]


@frappe.whitelist()
def get_project_members(project: str) -> dict:
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_owner_for(project, user)
    candidates = _pomas_users()
    owner = frappe.db.get_value("Project", project, "owner")
    roles = {row.user: row.project_role for row in frappe.get_all("PMS Project Member", filters={"project": project}, fields=["user", "project_role"], ignore_permissions=True)}
    all_members = _project_member_users(project)
    admins = [member.name for member in candidates if member.name in all_members and (member.name == owner or roles.get(member.name) == "Project Manager")]
    members = [member.name for member in candidates if member.name in all_members and member.name != owner and roles.get(member.name, "Member") == "Member"]
    return {"owner": owner, "admins": admins, "members": members, "candidates": candidates}


@frappe.whitelist()
def update_project_members(project: str, members: list[str] | str | None = None) -> dict:
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_owner_for(project, user)
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project not found."), frappe.DoesNotExistError)

    selected = _normalize_users(members)
    if len(selected) > 100:
        frappe.throw(_("A project can have at most 100 members."))
    allowed = {candidate.name for candidate in _pomas_users()}
    if any(member not in allowed for member in selected):
        frappe.throw(_("Select enabled Pomas users only."), frappe.PermissionError)

    owner = frappe.db.get_value("Project", project, "owner")
    previous_members = _project_member_users(project)
    selected = list(dict.fromkeys([*selected, owner] if owner else selected))
    removed_members = previous_members.difference(selected)
    task_names = frappe.get_all("Task", filters={"project": project}, pluck="name", ignore_permissions=True)
    reopened_tasks: list[str] = []
    if removed_members and task_names:
        reopened_tasks = list(dict.fromkeys(frappe.get_all("ToDo", filters={"allocated_to": ["in", sorted(removed_members)], "reference_type": "Task", "reference_name": ["in", task_names], "status": ["!=", "Cancelled"]}, pluck="reference_name", ignore_permissions=True)))
        if reopened_tasks:
            frappe.db.delete("ToDo", {"reference_type": "Task", "reference_name": ["in", reopened_tasks]})
            for task_name in reopened_tasks:
                frappe.db.set_value("Task", task_name, "status", "Open", update_modified=True)

    frappe.db.delete("Project User", {"parent": project, "parenttype": "Project"})
    for member in selected:
        frappe.get_doc({"doctype": "Project User", "parent": project, "parenttype": "Project", "parentfield": "users", "user": member, "welcome_email_sent": 1}).insert(ignore_permissions=True)
        if member == owner:
            _upsert_project_member(project, member, "Owner")
        elif not frappe.db.exists("PMS Project Member", {"project": project, "user": member}):
            _upsert_project_member(project, member, "Member")
    if removed_members:
        frappe.db.delete("PMS Project Member", {"project": project, "user": ["in", sorted(removed_members)]})
    return {"members": selected, "removed_members": sorted(removed_members), "reopened_tasks": reopened_tasks}


@frappe.whitelist()
def set_project_member_role(project: str, member: str, project_role: str) -> dict:
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_owner_for(project, user)
    member = (member or "").strip()
    if member == frappe.db.get_value("Project", project, "owner"):
        frappe.throw(_("The Project Owner is always an admin."), frappe.ValidationError)
    if member not in _project_member_users(project):
        frappe.throw(_("Add this user to the Project before changing their role."), frappe.ValidationError)
    if project_role not in {"Project Manager", "Member"}:
        frappe.throw(_("Choose Project Manager or Member."), frappe.ValidationError)
    _upsert_project_member(project, member, project_role)
    return {"member": member, "project_role": project_role}


def _parse_github_repository_url(repository_url: str) -> tuple[str, str, str]:
    value = (repository_url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com" or parsed.query or parsed.fragment:
        frappe.throw(_("Enter a GitHub repository URL such as https://github.com/owner/repository."), frappe.ValidationError)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        frappe.throw(_("Enter one GitHub repository URL with an owner and repository name."), frappe.ValidationError)
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not owner or not repository or not GITHUB_REPOSITORY_URL_PATTERN.fullmatch(owner) or not GITHUB_REPOSITORY_URL_PATTERN.fullmatch(repository):
        frappe.throw(_("Enter a valid GitHub owner and repository name."), frappe.ValidationError)
    return owner, repository, f"https://github.com/{owner}/{repository}"



def _github_link_payload(project: str) -> dict | None:
    link = frappe.db.get_value("PMS GitHub Project Link", {"project": project}, ["repository_url", "repository_owner", "repository_name", "connection_mode", "connection_status"], as_dict=True)
    return dict(link) if link else None


def _github_installation_token() -> str:
    settings = frappe.get_single("PMS GitHub Settings")
    app_id = (settings.app_id or "").strip()
    installation_id = (settings.installation_id or "").strip()
    encoded_key = settings.get_password("private_key", raise_exception=False)
    if not settings.enabled or not app_id.isdigit() or not installation_id.isdigit() or not encoded_key:
        frappe.throw(_("Complete and enable PMS GitHub Settings first."), frappe.ValidationError)
    try:
        raw_key = encoded_key.strip()
        pem_match = re.fullmatch(r"(-----BEGIN [A-Z ]+PRIVATE KEY-----)\s*([A-Za-z0-9+/=\s]+?)\s*(-----END [A-Z ]+PRIVATE KEY-----)", raw_key)
        if pem_match:
            header, payload, footer = pem_match.groups()
            payload = re.sub(r"\s+", "", payload)
            private_key = f"{header}\n" + "\n".join(payload[index:index + 64] for index in range(0, len(payload), 64)) + f"\n{footer}\n"
        else:
            private_key = base64.b64decode(re.sub(r"\s+", "", raw_key), validate=True).decode("utf-8")
        now = int(time.time())
        app_token = jwt.encode({"iat": now - 60, "exp": now + 540, "iss": app_id}, private_key, algorithm="RS256")
        response = requests.post(f"{GITHUB_API_URL}/app/installations/{installation_id}/access_tokens", headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {app_token}", "X-GitHub-Api-Version": "2022-11-28"}, timeout=12)
        response.raise_for_status()
        return response.json()["token"]
    except (ValueError, UnicodeDecodeError, jwt.PyJWTError, requests.RequestException, KeyError):
        frappe.throw(_("The GitHub private key must be a valid Base64-encoded .pem file."), frappe.ValidationError)


def _verify_github_link(project: str) -> dict:
    link_name = frappe.db.get_value("PMS GitHub Project Link", {"project": project}, "name")
    if not link_name:
        frappe.throw(_("Link a GitHub repository first."), frappe.DoesNotExistError)
    link = frappe.get_doc("PMS GitHub Project Link", link_name)
    organization = (frappe.get_single("PMS GitHub Settings").organization or "").strip().lower()
    if organization and link.repository_owner.lower() != organization:
        frappe.throw(_("This repository is outside the configured Pomas GitHub organization."), frappe.PermissionError)
    try:
        response = requests.get(f"{GITHUB_API_URL}/repos/{link.repository_owner}/{link.repository_name}", headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {_github_installation_token()}", "X-GitHub-Api-Version": "2022-11-28"}, timeout=12)
        response.raise_for_status()
    except requests.RequestException:
        link.connection_status = "Failed"
        link.save(ignore_permissions=True)
        frappe.throw(_("Pomas could not verify this repository. Check the App installation and selected repositories."), frappe.ValidationError)
    link.connection_status = "Connected"
    link.save(ignore_permissions=True)
    return _github_link_payload(project) or {}


def _save_github_link(project: str, repository_url: str) -> dict:
    owner, repository, normalized_url = _parse_github_repository_url(repository_url)
    existing = frappe.db.get_value("PMS GitHub Project Link", {"project": project}, "name")
    duplicate_project = frappe.db.get_value("PMS GitHub Project Link", {"repository_url": normalized_url}, "project")
    if duplicate_project and duplicate_project != project:
        frappe.throw(_("This GitHub repository is already linked to another Pomas Project."), frappe.ValidationError)
    if existing:
        link = frappe.get_doc("PMS GitHub Project Link", existing)
        link.repository_url = normalized_url
        link.repository_owner = owner
        link.repository_name = repository
        link.connection_mode = "Existing repository"
        link.connection_status = "Unverified"
        link.save(ignore_permissions=True)
    else:
        link = frappe.get_doc({
            "doctype": "PMS GitHub Project Link",
            "project": project,
            "repository_url": normalized_url,
            "repository_owner": owner,
            "repository_name": repository,
            "connection_mode": "Existing repository",
            "connection_status": "Unverified",
        })
        link.insert(ignore_permissions=True)
    return _github_link_payload(project) or {}


PROJECT_LOGO_FIELD = "pomas_project_logo"


def _project_logo_url(project: str) -> str | None:
    return frappe.db.get_value(
        "File",
        {"attached_to_doctype": "Project", "attached_to_name": project, "attached_to_field": PROJECT_LOGO_FIELD},
        "file_url",
        order_by="creation desc",
    )


@frappe.whitelist()
def upload_project_logo(project: str) -> dict:
    """Attach one public, centred 192px PNG logo to an authorized Project."""
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_owner_for(project, user)
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project not found."), frappe.DoesNotExistError)

    upload = frappe.request.files.get("logo")
    if not upload or not upload.filename:
        frappe.throw(_("Choose a PNG project logo."), frappe.ValidationError)
    filename = upload.filename.replace("\\", "/").rsplit("/", 1)[-1]
    content = upload.stream.read()
    if not filename.lower().endswith(".png") or not content.startswith(b"\x89PNG\r\n\x1a\n"):
        frappe.throw(_("Project logos must be PNG files."), frappe.ValidationError)
    if len(content) > 5 * 1024 * 1024:
        frappe.throw(_("Project logos must be 5 MB or smaller."), frappe.ValidationError)

    try:
        source = Image.open(BytesIO(content))
        source.load()
        normalized = ImageOps.fit(
            ImageOps.exif_transpose(source).convert("RGBA"),
            (192, 192),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        output = BytesIO()
        normalized.save(output, format="PNG", optimize=True)
        content = output.getvalue()
    except (OSError, ValueError):
        frappe.throw(_("The selected logo could not be processed as a PNG image."), frappe.ValidationError)

    filename = f"{project}-logo.png"

    old_files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Project", "attached_to_name": project, "attached_to_field": PROJECT_LOGO_FIELD},
        pluck="name",
        ignore_permissions=True,
    )
    stored_file = save_file(filename, content, "Project", project, is_private=0)
    stored_file.attached_to_field = PROJECT_LOGO_FIELD
    stored_file.save(ignore_permissions=True)
    for old_file in old_files:
        if old_file != stored_file.name and frappe.db.exists("File", old_file):
            frappe.delete_doc("File", old_file, force=True, ignore_permissions=True)
    return {"logo": stored_file.file_url}

@frappe.whitelist()
def complete_project(project: str) -> dict:
    """Mark a Project as completed without changing its individual Task records."""
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_owner_for(project, user)
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project not found."), frappe.DoesNotExistError)

    project_doc = frappe.get_doc("Project", project)
    project_doc.status = "Completed"
    project_doc.percent_complete = 100
    project_doc.save(ignore_permissions=True)
    return {"name": project_doc.name, "status": project_doc.status, "percent_complete": project_doc.percent_complete}


@frappe.whitelist()
def delete_project(project: str, confirmation: str) -> dict:
    """Permanently remove a Project and Pomas-owned work records after an exact-name confirmation."""
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_owner_for(project, user)
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project not found."), frappe.DoesNotExistError)

    project_doc = frappe.get_doc("Project", project)
    if (confirmation or "").strip() != project_doc.project_name:
        frappe.throw(_("Type the exact Project name to permanently delete it."), frappe.ValidationError)

    submissions = frappe.get_all(
        "PMS Work Submission", filters={"project": project}, fields=["name"], ignore_permissions=True
    )
    for submission in submissions:
        file_names = frappe.get_all(
            "PMS Work Submission File",
            filters={"parent": submission.name, "parenttype": "PMS Work Submission"},
            pluck="file",
            ignore_permissions=True,
        )
        for file_name in file_names:
            if file_name and frappe.db.exists("File", file_name):
                frappe.delete_doc("File", file_name, force=True, ignore_permissions=True)
        frappe.delete_doc("PMS Work Submission", submission.name, force=True, ignore_permissions=True)

    task_names = frappe.get_all("Task", filters={"project": project}, pluck="name", ignore_permissions=True)
    if task_names:
        frappe.db.delete("ToDo", {"reference_type": "Task", "reference_name": ["in", task_names]})
    for task_name in task_names:
        frappe.delete_doc("Task", task_name, force=True, ignore_permissions=True)

    github_link = frappe.db.get_value("PMS GitHub Project Link", {"project": project}, "name")
    if github_link:
        frappe.delete_doc("PMS GitHub Project Link", github_link, force=True, ignore_permissions=True)
    frappe.delete_doc("Project", project, force=True, ignore_permissions=True)
    return {"name": project}
@frappe.whitelist()
def create_task(
    project: str,
    subject: str,
    status: str = "Open",
    priority: str = "Medium",
    assigned_to: str | None = None,
    assigned_to_users: list[str] | str | None = None,
    exp_start_date: str | None = None,
    exp_end_date: str | None = None,
    expected_time: float | str | None = None,
    description: str | None = None,
    is_milestone: bool | int | str = False,
) -> dict:
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_manager_for(project, user)

    subject = (subject or "").strip()
    status = (status or "Open").strip()
    priority = (priority or "Medium").strip()
    assigned_to = (assigned_to or "").strip()
    assignees = _normalize_users(assigned_to_users, assigned_to)
    description = (description or "").strip()
    expected_hours = frappe.utils.flt(expected_time or 0)

    if not subject:
        frappe.throw(_("Task name is required."))
    if len(subject) > 140:
        frappe.throw(_("Task name cannot exceed 140 characters."))
    if status not in TASK_CREATE_STATUSES:
        frappe.throw(_("Select a valid starting status."))
    if priority not in TASK_PRIORITIES:
        frappe.throw(_("Select a valid priority."))
    if expected_hours < 0:
        frappe.throw(_("Estimated hours cannot be negative."))
    if len(description) > 10000:
        frappe.throw(_("Description cannot exceed 10,000 characters."))

    _validate_project_users(project, assignees)

    task = frappe.get_doc(
        {
            "doctype": "Task",
            "project": project,
            "subject": subject,
            "status": status,
            "priority": priority,
            "exp_start_date": exp_start_date or None,
            "exp_end_date": exp_end_date or None,
            "expected_time": expected_hours,
            "description": "<br>".join(escape_html(description).splitlines()) if description else None,
            "is_milestone": frappe.utils.cint(is_milestone),
        }
    )
    task.insert(ignore_permissions=True)

    if assignees:
        for assignee in assignees:


            _create_assignment(task, assignee, user)
        task.status = "Working"
        task.save(ignore_permissions=True)

    return {
        "name": task.name,
        "subject": task.subject,
        "status": task.status,
        "priority": task.priority,
        "assignees": assignees,
    }


@frappe.whitelist()
def get_project_github_link(project: str) -> dict | None:
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    return _github_link_payload(project)


@frappe.whitelist()
def link_project_github_repository(project: str, repository_url: str) -> dict:
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_manager_for(project, user)
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project not found."), frappe.DoesNotExistError)
    return _save_github_link(project, repository_url)


@frappe.whitelist()
def unlink_project_github_repository(project: str) -> dict:
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_manager_for(project, user)
    link = frappe.db.get_value("PMS GitHub Project Link", {"project": project}, "name")
    if link:
        frappe.delete_doc("PMS GitHub Project Link", link, force=True, ignore_permissions=True)
    return {"project": project}


@frappe.whitelist()
def verify_project_github_repository(project: str) -> dict:
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_manager_for(project, user)
    return _verify_github_link(project)


@frappe.whitelist()
def create_project_github_repository(project: str, repository_name: str) -> dict:
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _require_project_manager_for(project, user)
    repository_name = (repository_name or "").strip()
    if not GITHUB_REPOSITORY_URL_PATTERN.fullmatch(repository_name):
        frappe.throw(_("Use letters, numbers, dots, hyphens, or underscores for the repository name."), frappe.ValidationError)
    if frappe.db.exists("PMS GitHub Project Link", {"project": project}):
        frappe.throw(_("This Project already has a GitHub repository link."), frappe.ValidationError)
    organization = (frappe.get_single("PMS GitHub Settings").organization or "").strip()
    if not organization:
        frappe.throw(_("Set the connected GitHub organization in PMS GitHub Settings first."), frappe.ValidationError)
    try:
        response = requests.post(f"{GITHUB_API_URL}/orgs/{organization}/repos", json={"name": repository_name, "private": True, "description": f"Pomas Project: {frappe.db.get_value('Project', project, 'project_name') or project}"}, headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {_github_installation_token()}", "X-GitHub-Api-Version": "2022-11-28"}, timeout=12)
        response.raise_for_status()
    except requests.RequestException:
        frappe.throw(_("Pomas could not create the repository. Check the GitHub App permission and repository name."), frappe.ValidationError)
    normalized_url = f"https://github.com/{organization}/{repository_name}"
    frappe.get_doc({"doctype": "PMS GitHub Project Link", "project": project, "repository_url": normalized_url, "repository_owner": organization, "repository_name": repository_name, "connection_mode": "Created by Pomas", "connection_status": "Connected"}).insert(ignore_permissions=True)
    return _github_link_payload(project) or {}

@frappe.whitelist()
def delete_task(task: str) -> dict:
    """Permanently delete an authorized manager’s unassigned Open Task."""
    user = _require_user()
    _require_pms_access(user)
    task_doc = frappe.get_doc("Task", task)
    _assert_project_access(task_doc.project, user)
    _require_project_manager_for(task_doc.project, user)
    if task_doc.status != "Open" or _task_assignees(task):
        frappe.throw(_("Only unassigned Open Tasks can be deleted."), frappe.PermissionError)
    frappe.db.delete("ToDo", {"reference_type": "Task", "reference_name": task})
    frappe.delete_doc("Task", task, force=True, ignore_permissions=True)
    return {"name": task}


@frappe.whitelist()
def get_session() -> dict:
    user = _require_user()
    roles = _require_pms_access(user)
    return {
        "user": user,
        "full_name": frappe.utils.get_fullname(user),
        "user_image": frappe.db.get_value("User", user, "user_image"),
        "roles": sorted(roles.intersection(PMS_ROLES)),
        "is_administrator": _is_administrator(user),
        "can_manage_github": user == "Administrator" or "System Manager" in roles,
        "can_create_tasks": False,
        "can_create_projects": True,
    }


@frappe.whitelist()
def get_github_connection_summary() -> dict:
    """Return only the active organization label for authorized project managers."""
    user = _require_user()
    _require_pms_access(user)
    settings = frappe.get_single("PMS GitHub Settings")
    return {"enabled": bool(settings.enabled), "organization": (settings.organization or "").strip()}

@frappe.whitelist()
def create_project(
    project_name: str,
    expected_start_date: str | None = None,
    expected_end_date: str | None = None,
    priority: str = "Medium",
    description: str | None = None,
    customer: str | None = None,
    members: list[str] | str | None = None,
    github_repository_url: str | None = None,
) -> dict:
    user = _require_user()
    _require_pms_access(user)

    project_name = (project_name or "").strip()
    priority = (priority or "Medium").strip()
    description = (description or "").strip()
    customer = (customer or "").strip()
    github_repository_url = (github_repository_url or "").strip()
    if github_repository_url:
        _parse_github_repository_url(github_repository_url)
    requested_members = _normalize_users(members)
    selected_members = list(dict.fromkeys([*requested_members, user]))
    allowed_members = {member.name for member in _pomas_users()}
    if len(selected_members) > 100:
        frappe.throw(_("A project can have at most 100 members."))
    if any(member not in allowed_members for member in selected_members):
        frappe.throw(_("Select enabled Pomas users only."), frappe.PermissionError)
    if not project_name:
        frappe.throw(_("Project name is required."))
    if len(project_name) > 140:
        frappe.throw(_("Project name cannot exceed 140 characters."))
    if customer and not frappe.db.exists("Customer", customer):
        frappe.throw(_("Select an existing client or create one first."), frappe.ValidationError)
    if priority not in TASK_PRIORITIES:
        frappe.throw(_("Select a valid priority."))
    if expected_start_date and expected_end_date and expected_start_date > expected_end_date:
        frappe.throw(_("Due date must be on or after the start date."))
    if len(description) > 10000:
        frappe.throw(_("Description cannot exceed 10,000 characters."))

    project = frappe.get_doc(
        {
            "doctype": "Project",
            "project_name": project_name,
            "status": "Open",
            "priority": priority,
            "expected_start_date": expected_start_date or None,
            "expected_end_date": expected_end_date or None,
            "percent_complete_method": "Task Completion",
            "notes": "<br>".join(escape_html(description).splitlines()) if description else None,
            "customer": customer or None,
        }
    )
    project.insert(ignore_permissions=True)
    for member in selected_members:
        frappe.get_doc(
            {
                "doctype": "Project User",
                "parent": project.name,
                "parenttype": "Project",
                "parentfield": "users",
                "user": member,
                "welcome_email_sent": 1,
            }
        ).insert(ignore_permissions=True)
        _upsert_project_member(project.name, member, "Owner" if member == user else "Member")
    github = _save_github_link(project.name, github_repository_url) if github_repository_url else None
    return {"name": project.name, "project_name": project.project_name, "github": github}


def _require_github_settings_manager(user: str, roles: set[str]) -> None:
    if user != "Administrator" and "System Manager" not in roles:
        frappe.throw(_("Only a System Manager can manage the GitHub connection."), frappe.PermissionError)


@frappe.whitelist()
def get_github_connection_settings() -> dict:
    user = _require_user()
    _require_github_settings_manager(user, _require_pms_access(user))
    settings = frappe.get_single("PMS GitHub Settings")
    return {"enabled": bool(settings.enabled), "app_id": settings.app_id or "", "installation_id": settings.installation_id or "", "organization": settings.organization or ""}


@frappe.whitelist()
def save_github_connection_settings(enabled: int | bool, app_id: str, installation_id: str, organization: str, private_key: str | None = None) -> dict:
    user = _require_user()
    _require_github_settings_manager(user, _require_pms_access(user))
    app_id, installation_id, organization = (app_id or "").strip(), (installation_id or "").strip(), (organization or "").strip()
    if frappe.utils.cint(enabled) and (not app_id.isdigit() or not installation_id.isdigit() or not GITHUB_REPOSITORY_URL_PATTERN.fullmatch(organization)):
        frappe.throw(_("Enter a valid GitHub App ID, Installation ID, and organization name."), frappe.ValidationError)
    settings = frappe.get_single("PMS GitHub Settings")
    settings.enabled, settings.app_id, settings.installation_id, settings.organization = frappe.utils.cint(enabled), app_id, installation_id, organization
    if private_key:
        settings.private_key = private_key.strip()
    settings.save(ignore_permissions=True)
    return get_github_connection_settings()


@frappe.whitelist()
def test_github_connection() -> dict:
    user = _require_user()
    _require_github_settings_manager(user, _require_pms_access(user))
    token = _github_installation_token()
    try:
        response = requests.get(f"{GITHUB_API_URL}/installation/repositories", headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"}, timeout=12)
        response.raise_for_status()
    except requests.RequestException:
        frappe.throw(_("Pomas could not reach the configured GitHub installation."), frappe.ValidationError)
    return {"connected": True}


@frappe.whitelist()
def get_projects() -> list[dict]:
    user = _require_user()
    _require_pms_access(user)
    filters: dict = {"status": ["!=", "Cancelled"]}
    if not _is_administrator(user):
        project_names = _member_project_names(user)
        if not project_names:
            return []
        filters["name"] = ["in", sorted(project_names)]

    projects = frappe.get_all(
        "Project",
        filters=filters,
        fields=[
            "name",
            "project_name",
            "status",
            "percent_complete",
            "expected_start_date",
            "expected_end_date",
            "modified",
            "customer",
        ],
        order_by="modified desc",
        ignore_permissions=True,
    )
    for project in projects:
        project["logo"] = _project_logo_url(project.name)
        project["project_role"] = _project_role(project.name, user)
        project["can_manage"] = _can_manage_project(project.name, user)
        project["can_manage_team"] = _project_role(project.name, user) == "Owner"
        project["github"] = _github_link_payload(project.name)
        task_names = frappe.get_all(
            "Task",
            filters={"project": project.name, "status": ["in", BOARD_STATUSES]},
            pluck="name",
            ignore_permissions=True,
        )
        project["task_count"] = len(task_names)
        assigned_tasks = set()
        if task_names:
            assigned_tasks = set(
                frappe.get_all(
                    "ToDo",
                    filters={
                        "reference_type": "Task",
                        "reference_name": ["in", task_names],
                        "status": ["!=", "Cancelled"],
                    },
                    pluck="reference_name",
                    ignore_permissions=True,
                )
            )
        project["unassigned_task_count"] = len(task_names) - len(assigned_tasks)
    return projects


@frappe.whitelist()
def get_board(project: str) -> dict:
    user = _require_user()
    _require_pms_access(user)
    _assert_project_access(project, user)
    _sync_overdue_tasks(project)
    _sync_due_priorities(project)

    project_doc = frappe.get_value(
        "Project",
        project,
        ["name", "project_name", "status", "percent_complete", "expected_end_date", "customer"],
        as_dict=True,
    )
    if not project_doc:
        frappe.throw(_("Project not found."), frappe.DoesNotExistError)
    project_doc["logo"] = _project_logo_url(project)
    project_doc["github"] = _github_link_payload(project)
    project_doc["project_role"] = _project_role(project, user)
    project_doc["can_manage"] = _can_manage_project(project, user)
    project_doc["can_manage_team"] = _project_role(project, user) == "Owner"

    tasks = frappe.get_all(
        "Task",
        filters={"project": project, "status": ["in", BOARD_STATUSES]},
        fields=[
            "name",
            "subject",
            "status",
            "priority",
            "exp_end_date",
            "progress",
            "is_milestone",
            "_assign",
            "modified",
        ],
        ignore_permissions=True,
    )

    columns = []
    for status in BOARD_STATUSES:
        column_tasks = []
        for task in tasks:
            if task.status != status:
                continue
            task["assignees"] = _task_assignees(task.name)
            column_tasks.append(task)
        columns.append({"status": status, "tasks": column_tasks})

    return {"project": project_doc, "columns": columns}


@frappe.whitelist()
def open_submission_file(task: str, file: str) -> None:
    """Open a privately stored submission file after verifying Project access."""
    user = _require_user()
    _require_pms_access(user)
    task_project = frappe.db.get_value("Task", task, "project")
    if not task_project:
        frappe.throw(_("Task not found."), frappe.DoesNotExistError)
    _assert_project_access(task_project, user)
    submitted_file = frappe.db.get_value(
        "PMS Work Submission File",
        {"name": file, "parenttype": "PMS Work Submission"},
        ["parent", "file"],
        as_dict=True,
    )
    if not submitted_file or not submitted_file.file:
        frappe.throw(_("Submitted file not found."), frappe.DoesNotExistError)
    if frappe.db.get_value("PMS Work Submission", submitted_file.parent, "task") != task:
        frappe.throw(_("That file does not belong to this task."), frappe.PermissionError)
    stored_file = frappe.get_doc("File", submitted_file.file)
    frappe.local.response.filename = stored_file.file_name
    frappe.local.response.filecontent = stored_file.get_content()
    frappe.local.response.type = "download"
    frappe.local.response.display_content_as = "inline"


@frappe.whitelist()
def get_task_details(task: str) -> dict:
    user = _require_user()
    _require_pms_access(user)
    task_doc = frappe.get_value(
        "Task",
        task,
        [
            "name", "subject", "project", "status", "priority", "exp_start_date",
            "exp_end_date", "expected_time", "progress", "description", "is_milestone", "modified",
        ],
        as_dict=True,
    )
    if not task_doc:
        frappe.throw(_("Task not found."), frappe.DoesNotExistError)
    _assert_project_access(task_doc.project, user)
    _sync_overdue_tasks(task_doc.project)
    task_doc = frappe.get_value(
        "Task", task,
        ["name", "subject", "project", "status", "priority", "exp_start_date", "exp_end_date", "expected_time", "progress", "description", "is_milestone", "modified"],
        as_dict=True,
    )
    project_name = frappe.db.get_value("Project", task_doc.project, "project_name")
    return _task_payload(task_doc, project_name)


@frappe.whitelist()
def take_task(task: str) -> dict:
    user = _require_user()
    _require_pms_access(user)
    task_rows = frappe.db.sql(
        """select name, subject, project, status, priority, exp_start_date, exp_end_date,
                  expected_time, progress, description, is_milestone, modified
             from `tabTask` where name=%s for update""",
        task,
        as_dict=True,
    )
    if not task_rows:
        frappe.throw(_("Task not found."), frappe.DoesNotExistError)
    task_doc = task_rows[0]
    _assert_project_access(task_doc.project, user)
    if task_doc.status not in {"Open", "Overdue"}:
        frappe.throw(_("Only unassigned Open or Overdue tasks can be taken."))
    if _task_assignees(task):
        frappe.throw(_("This task has already been assigned."))
    _create_assignment(task_doc, user, user)
    frappe.db.set_value("Task", task_doc.name, "status", "Working", update_modified=True)
    task_doc.status = "Working"
    project_name = frappe.db.get_value("Project", task_doc.project, "project_name")
    return _task_payload(task_doc, project_name)


@frappe.whitelist()
def update_open_task(
    task: str,
    subject: str,
    priority: str,
    assigned_to: str | None = None,
    assigned_to_users: list[str] | str | None = None,
    exp_start_date: str | None = None,
    exp_end_date: str | None = None,
    expected_time: float | str | None = None,
    description: str | None = None,
    is_milestone: bool | int | str = False,
) -> dict:
    user = _require_user()
    roles = _require_pms_access(user)
    task_rows = frappe.db.sql(
        "select name, project, status from `tabTask` where name=%s for update", task, as_dict=True
    )
    if not task_rows:
        frappe.throw(_("Task not found."), frappe.DoesNotExistError)
    task_row = task_rows[0]
    _assert_project_access(task_row.project, user)
    _require_project_manager_for(task_row.project, user)
    if task_row.status != "Open" or _task_assignees(task):
        frappe.throw(_("Only an unassigned Open task can be edited."))

    subject = (subject or "").strip()
    priority = (priority or "Medium").strip()
    assigned_to = (assigned_to or "").strip()
    assignees = _normalize_users(assigned_to_users, assigned_to)
    description = (description or "").strip()
    expected_hours = frappe.utils.flt(expected_time or 0)
    if not subject:
        frappe.throw(_("Task name is required."))
    if len(subject) > 140:
        frappe.throw(_("Task name cannot exceed 140 characters."))
    if customer and not frappe.db.exists("Customer", customer):
        frappe.throw(_("Select a valid priority."))
    if expected_hours < 0:
        frappe.throw(_("Estimated hours cannot be negative."))
    if len(description) > 10000:
        frappe.throw(_("Description cannot exceed 10,000 characters."))
    if exp_start_date and exp_end_date and exp_start_date > exp_end_date:
        frappe.throw(_("Due date must be on or after the start date."))
    _validate_project_users(task_row.project, assignees)

    task_doc = frappe.get_doc("Task", task)
    task_doc.subject = subject
    task_doc.priority = priority
    task_doc.exp_start_date = exp_start_date or None
    task_doc.exp_end_date = exp_end_date or None
    task_doc.expected_time = expected_hours
    task_doc.description = "<br>".join(escape_html(description).splitlines()) if description else None
    task_doc.is_milestone = frappe.utils.cint(is_milestone)
    task_doc.save(ignore_permissions=True)
    if assignees:
        for assignee in assignees:
            _create_assignment(task_doc, assignee, user)
        task_doc.status = "Working"
        task_doc.save(ignore_permissions=True)
    project_name = frappe.db.get_value("Project", task_doc.project, "project_name")
    return _task_payload(task_doc, project_name)


@frappe.whitelist()
def review_task(task: str, action: str) -> dict:
    user = _require_user()
    roles = _require_pms_access(user)
    task_rows = frappe.db.sql(
        "select name, project, status from `tabTask` where name=%s for update", task, as_dict=True
    )
    if not task_rows:
        frappe.throw(_("Task not found."), frappe.DoesNotExistError)
    task_row = task_rows[0]
    _assert_project_access(task_row.project, user)
    _require_project_manager_for(task_row.project, user)
    if task_row.status != "Pending Review":
        frappe.throw(_("Only tasks awaiting review can be approved or rejected."))
    action = (action or "").strip().lower()
    if action not in {"approve", "reject"}:
        frappe.throw(_("Select approve or reject."))

    if action == "approve":
        # Task.save() asks ERPNext to close assignments through Desk permissions.
        # PMS intentionally keeps that access inside its own API, so update the
        # task and its assignments explicitly after the manager authorization.
        frappe.db.set_value(
            "Task", task, {"status": "Completed", "progress": 100}, update_modified=True
        )
        frappe.db.set_value(
            "ToDo",
            {"reference_type": "Task", "reference_name": task, "status": ["!=", "Cancelled"]},
            "status",
            "Closed",
            update_modified=True,
        )
        task_doc = frappe.get_doc("Task", task)
        project_doc = frappe.get_doc("Project", task_doc.project)
        project_doc.update_percent_complete()
        frappe.db.set_value(
            "Project", project_doc.name, "percent_complete", project_doc.percent_complete, update_modified=True
        )
    else:
        frappe.db.set_value("Task", task, "status", "Working", update_modified=True)
        task_doc = frappe.get_doc("Task", task)
    project_name = frappe.db.get_value("Project", task_doc.project, "project_name")
    return _task_payload(task_doc, project_name)

@frappe.whitelist()
def submit_task_work(task: str, description: str, file_metadata: list[dict] | str | None = None) -> dict:
    """Record work and move the assigned Task into Pending Review."""
    user = _require_user()
    _require_pms_access(user)
    task_doc = frappe.get_value(
        "Task",
        task,
        ["name", "subject", "project", "status"],
        as_dict=True,
    )
    if not task_doc:
        frappe.throw(_("Task not found."), frappe.DoesNotExistError)
    _assert_project_access(task_doc.project, user)
    if task_doc.status not in {"Working", "Overdue"}:
        frappe.throw(_("Only active Working or Overdue tasks can be submitted for review."))
    if user not in _task_assignees(task):
        frappe.throw(_("Only a user assigned to this task can submit work."), frappe.PermissionError)

    description = (description or "").strip()
    if not description:
        frappe.throw(_("Describe the work you completed."))
    if len(description) > 10000:
        frappe.throw(_("Submission description cannot exceed 10,000 characters."))

    if isinstance(file_metadata, str):
        try:
            file_metadata = json.loads(file_metadata)
        except (TypeError, ValueError):
            frappe.throw(_("File details must be valid JSON."))
    if file_metadata is None:
        file_metadata = []
    if not isinstance(file_metadata, list):
        frappe.throw(_("File details must be a list."))
    uploads = list(frappe.request.files.getlist("files")) if frappe.request and frappe.request.files else []
    if len(uploads) != len(file_metadata):
        frappe.throw(_("Every selected file must have one repository destination."))
    if len(uploads) > 25:
        frappe.throw(_("A submission can contain at most 25 uploaded files."))

    clean_files = []
    for upload, file_entry in zip(uploads, file_metadata, strict=True):
        if not isinstance(file_entry, dict):
            frappe.throw(_("Each selected file must have a repository destination."))
        supplied_name = (upload.filename or "").strip().replace("\\", "/")
        file_name = os.path.basename(supplied_name)
        repository_path = str(file_entry.get("repository_path") or "").strip().replace("\\", "/")
        path_parts = repository_path.split("/")
        if not file_name:
            frappe.throw(_("Every uploaded file needs a file name."))
        if len(file_name) > 255:
            frappe.throw(_("File names cannot exceed 255 characters."))
        if not repository_path:
            frappe.throw(_("Every uploaded file needs a repository destination."))
        if len(repository_path) > 1000:
            frappe.throw(_("Repository destinations cannot exceed 1,000 characters."))
        if repository_path.startswith("/") or ":" in path_parts[0] or any(
            part in {"", ".", ".."} for part in path_parts
        ):
            frappe.throw(_("Repository destinations must be safe relative paths."))
        clean_files.append(
            {"file_name": file_name, "repository_path": repository_path, "file_size": 0}
        )

    submission = frappe.get_doc(
        {
            "doctype": "PMS Work Submission",
            "task": task_doc.name,
            "project": task_doc.project,
            "submitted_by": user,
            "submitted_on": frappe.utils.now_datetime(),
            "description": description,
            "files": [],
        }
    )
    submission.insert(ignore_permissions=True)

    for upload, file_entry in zip(uploads, clean_files, strict=True):
        stored_file = save_file(
            file_entry["file_name"],
            upload.stream.read(),
            submission.doctype,
            submission.name,
            is_private=1,
        )
        submission.append(
            "files",
            {
                **file_entry,
                "file": stored_file.name,
                "file_size": stored_file.file_size,
            },
        )
    if uploads:
        submission.save(ignore_permissions=True)

    review_task_doc = frappe.get_doc("Task", task_doc.name)
    review_task_doc.status = "Pending Review"
    review_task_doc.save(ignore_permissions=True)

    return {
        "name": submission.name,
        "task": task_doc.name,
        "submitted_on": submission.submitted_on,
        "file_count": len(uploads),
        "status": "Pending Review",
    }


@frappe.whitelist()
def get_my_tasks() -> list[dict]:
    user = _require_user()
    _require_pms_access(user)
    task_names = frappe.get_all(
        "ToDo",
        filters={
            "allocated_to": user,
            "reference_type": "Task",
            "status": ["!=", "Cancelled"],
        },
        pluck="reference_name",
        ignore_permissions=True,
    )
    if not task_names:
        return []

    filters = {"name": ["in", task_names], "status": ["in", BOARD_STATUSES]}
    if not _is_administrator(user):
        projects = _member_project_names(user)
        if not projects:
            return []
        filters["project"] = ["in", sorted(projects)]
    tasks = frappe.get_all(
        "Task",
        filters=filters,
        fields=[
            "name", "subject", "project", "status", "priority", "exp_end_date",
            "progress", "modified",
        ],
        order_by="modified desc",
        ignore_permissions=True,
    )
    project_names = {
        project.name: project.project_name
        for project in frappe.get_all(
            "Project",
            filters={"name": ["in", sorted({task.project for task in tasks})]},
            fields=["name", "project_name"],
            ignore_permissions=True,
        )
    }
    return [_task_payload(task, project_names.get(task.project)) for task in tasks]

@frappe.whitelist(allow_guest=True)
def signup(full_name: str, email: str, password: str) -> dict:
    """Create a self-service Pomas Website User with no elevated privileges."""
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""
    if len(full_name) < 2 or len(full_name) > 140:
        frappe.throw(_("Enter a name between 2 and 140 characters."))
    if not frappe.utils.validate_email_address(email, throw=False):
        frappe.throw(_("Enter a valid email address."))
    if len(password) < 10:
        frappe.throw(_("Choose a password with at least 10 characters."))
    if frappe.db.exists("User", email):
        frappe.throw(_("An account already exists for this email. Please sign in instead."))
    if not frappe.db.exists("Role", "PMS User"):
        frappe.throw(_("PMS access is not configured yet. Please contact an administrator."))

    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": full_name,
        "enabled": 1,
        "user_type": "Website User",
        "new_password": password,
        "send_welcome_email": 0,
    })
    user.insert(ignore_permissions=True)
    user.append_roles("PMS User")
    user.save(ignore_permissions=True)
    return {"user": user.name}

@frappe.whitelist(allow_guest=True)
def get_social_login_options() -> list[dict]:
    """Return only fully configured Pomas social sign-up providers and their OAuth URLs."""
    from frappe.integrations.doctype.social_login_key.social_login_key import provider_allows_signup
    from frappe.utils.oauth import get_oauth2_authorize_url
    from frappe.utils.password import get_decrypted_password

    options = []
    for provider, label in (("google", "Google"), ("github", "GitHub")):
        settings = frappe.db.get_value(
            "Social Login Key",
            provider,
            ["enable_social_login", "client_id", "base_url"],
            as_dict=True,
        )
        if not settings or not settings.enable_social_login or not settings.client_id or not settings.base_url:
            continue
        if not get_decrypted_password("Social Login Key", provider, "client_secret", raise_exception=False):
            continue
        if not provider_allows_signup(provider):
            continue
        try:
            options.append({"provider": provider, "label": label, "url": get_oauth2_authorize_url(provider, "/pms")})
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Pomas {label} social login setup")
    return options
