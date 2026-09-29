from __future__ import annotations

import frappe


POMAS_SOCIAL_PROVIDERS = {"google", "github"}


def provision_social_pms_user(user, method=None) -> None:
    """Give a newly created Google/GitHub Website User baseline Pomas access only."""
    if user.user_type != "Website User" or not frappe.db.exists("Role", "PMS User"):
        return
    providers = {entry.provider.lower() for entry in user.get("social_logins", []) if entry.provider}
    if not providers.intersection(POMAS_SOCIAL_PROVIDERS):
        return
    if "PMS User" not in frappe.get_roles(user.name):
        user.add_roles("PMS User")
