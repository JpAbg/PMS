# Pomas

Pomas is a Trello-like project-management workspace built as a custom Frappe and ERPNext app. It uses standard ERPNext Projects, Tasks, Customers, Contacts, Addresses, and Frappe assignments without changing upstream Frappe, ERPNext, or HRMS source files.

It provides a responsive Vue interface, a progressive web app foundation for Android distribution, project-scoped permissions, task review, work submissions, optional client records, and optional GitHub repository links.

## Main capabilities

- Project boards grouped by Open, Working, Pending Review, Overdue, and Completed.
- Project-scoped Owner, Project Manager, and Member authority using the `PMS Project Member` custom DocType.
- Task assignment, self-claiming, priority escalation before due dates, milestone markers, review/complete/reject workflow, and My Tasks.
- Desktop work submissions with optional private file attachments.
- Optional client selection and creation using ERPNext Customer, Contact, and Address records.
- Optional GitHub repository linking or private-repository creation through a configured GitHub App connection.
- Light and dark Pomas themes, a collapsible project sidebar, responsive board views, and a PWA manifest.

## Install

From a Frappe bench that already includes compatible ERPNext and HRMS versions:

```bash
bench get-app https://github.com/JpAbg/PMS --branch develop
bench --site your-site.localhost install-app pms
bench --site your-site.localhost migrate
```

The app exposes its web workspace at `/pms`.

## Frontend development

The Vue frontend is in `frontend/`. Install its dependencies and build it before using a production Frappe site:

```bash
cd apps/pms/frontend
yarn install
yarn build
bench --site your-site.localhost clear-cache
```

For local frontend development, run `yarn dev`. The Vite server uses the configured Frappe proxy settings.

## Configuration notes

- Assign the `PMS User` role to Pomas users. Project authority is then granted per project from the Pomas interface.
- Configure a GitHub App connection in Pomas Settings only if repository linking/creation is required. Keep private keys out of version control.
- Scheduler support is enabled for automatic overdue task updates; ensure the Frappe scheduler is running in deployed environments.

See [USER_GUIDE.md](USER_GUIDE.md) for day-to-day use.

## Contributing

Run the frontend build and relevant Python checks before submitting a change. The app uses Ruff, ESLint, Prettier, and PyUpgrade through its development tooling.

## License

MIT
