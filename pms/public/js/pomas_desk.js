(() => {
	const button_label = __("Open Pomas");
	const max_attempts = 12;

	function is_home_workspace() {
		const route = frappe.get_route();
		return (
			route[0] === "home" ||
			(route[0] === "Workspaces" && route[1] === "Home") ||
			frappe.workspace?.current_page?.name === "Home"
		);
	}

	function remove_button() {
		const page = frappe.workspace?.page;
		page?.inner_toolbar
			?.find(`button[data-label="${encodeURIComponent(button_label)}"]`)
			.remove();
	}

	function add_button(attempt = 0) {
		if (!is_home_workspace()) {
			remove_button();
			return;
		}

		const page = frappe.workspace?.page;
		if (!page?.add_inner_button) {
			if (attempt < max_attempts) {
				setTimeout(() => add_button(attempt + 1), 100);
			}
			return;
		}

		page
			.add_inner_button(button_label, () => window.location.assign("/pms"))
			.addClass("btn-primary");
	}

	function refresh_button() {
		setTimeout(() => add_button(), 0);
	}

	frappe.router.on("change", refresh_button);
	$(document).on("page-change", refresh_button);
	$(document).on("app_ready", refresh_button);
})();
