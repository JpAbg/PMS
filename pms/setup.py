import frappe
from frappe import _


PMS_PROJECT_MANAGER_ROLE = "PMS Project Manager"
LEGACY_PROJECT_ADMIN_ROLE = "PMS Project Admin"

PMS_ROLES = (
    "PMS Administrator",
    PMS_PROJECT_MANAGER_ROLE,
    "PMS User",
)
PROJECT_MEMBER_ROLES = {PMS_PROJECT_MANAGER_ROLE, "PMS User"}


def ensure_roles():
    """Create frontend-only application roles without broad ERPNext DocType access."""
    for role_name in PMS_ROLES:
        if frappe.db.exists("Role", role_name):
            role = frappe.get_doc("Role", role_name)
        else:
            role = frappe.get_doc({"doctype": "Role", "role_name": role_name})

        if role.is_new() or role.desk_access:
            role.desk_access = 0
            role.save(ignore_permissions=True)


def configure_project_member(user: str, project: str, role: str) -> dict:
    """Assign a scoped Pomas role and standard ERPNext Project membership."""
    if role not in PROJECT_MEMBER_ROLES:
        frappe.throw(_("Role must be PMS Project Manager or PMS User."))
    if not frappe.db.exists("User", user):
        frappe.throw(_("User {0} does not exist.").format(user))
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist.").format(project))

    user_doc = frappe.get_doc("User", user)
    user_doc.append_roles(role)
    user_doc.save(ignore_permissions=True)

    project_doc = frappe.get_doc("Project", project)
    if not any(row.user == user for row in project_doc.users):
        project_doc.append(
            "users",
            {
                "user": user,
                "welcome_email_sent": 1,
                "view_attachments": 1,
            },
        )
        project_doc.save(ignore_permissions=True)

    return {"user": user, "project": project, "role": role}


def after_install():
    ensure_roles()
