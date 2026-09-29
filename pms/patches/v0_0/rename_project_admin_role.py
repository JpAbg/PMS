import frappe

from pms.setup import LEGACY_PROJECT_ADMIN_ROLE, PMS_PROJECT_MANAGER_ROLE, ensure_roles


def execute():
    if frappe.db.exists("Role", LEGACY_PROJECT_ADMIN_ROLE):
        if not frappe.db.exists("Role", PMS_PROJECT_MANAGER_ROLE):
            frappe.rename_doc(
                "Role",
                LEGACY_PROJECT_ADMIN_ROLE,
                PMS_PROJECT_MANAGER_ROLE,
                force=True,
            )
        else:
            users = frappe.get_all(
                "Has Role",
                filters={
                    "role": LEGACY_PROJECT_ADMIN_ROLE,
                    "parenttype": "User",
                },
                pluck="parent",
            )
            for user in users:
                user_doc = frappe.get_doc("User", user)
                user_doc.append_roles(PMS_PROJECT_MANAGER_ROLE)
                user_doc.remove_roles(LEGACY_PROJECT_ADMIN_ROLE)
                user_doc.save(ignore_permissions=True)

            legacy_role = frappe.get_doc("Role", LEGACY_PROJECT_ADMIN_ROLE)
            legacy_role.disabled = 1
            legacy_role.save(ignore_permissions=True)

    ensure_roles()
