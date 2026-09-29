import frappe


def execute():
    for project in frappe.get_all("Project", fields=["name", "owner"], ignore_permissions=True):
        users = set(frappe.get_all("Project User", filters={"parent": project.name, "parenttype": "Project"}, pluck="user", ignore_permissions=True))
        if project.owner:
            users.add(project.owner)
        for user in users:
            role = "Owner" if user == project.owner else "Member"
            name = frappe.db.get_value("PMS Project Member", {"project": project.name, "user": user}, "name")
            if name:
                frappe.db.set_value("PMS Project Member", name, "project_role", role, update_modified=False)
            else:
                frappe.get_doc({"doctype": "PMS Project Member", "project": project.name, "user": user, "project_role": role}).insert(ignore_permissions=True)
