# Pomas User Guide

## Sign in and create an account

Open `/pms` and sign in with your Pomas account. New people can use **Create an account** on the sign-in screen. New accounts receive the basic `PMS User` role; they do not automatically receive access to any project.

## Projects and access

Create a project from **New project**. The creator becomes its Project Owner automatically.

- The Owner can edit project details, manage the team, promote or demote Project Managers, complete a project, and delete it.
- Project Managers can create, edit, assign, review, and delete tasks in that project.
- Members can view every task in projects they belong to, claim unassigned work, and submit their own assigned work.

Use the project menu beside Refresh to edit the project, its team, logo, client, or repository connection. Removing someone from a project immediately removes their access and unassigns their project tasks.

## Add a client

In **New project**, select an existing client or use **New client**.

The Client side page lets you choose **Organization** or **Individual**, then add a name, email, phone number, and optional billing address. Pomas creates standard ERPNext Customer, Contact, and Address records and selects the client for the project.

## Create and manage tasks

Project Owners and Project Managers use **New task** to add work. A task can have a due date, priority, description, milestone flag, and one or more project members assigned.

The normal lifecycle is:

1. **Open** — unassigned work; a manager can edit it.
2. **Working** — assigned or claimed work.
3. **Pending Review** — the assignee submitted work.
4. **Completed** — a manager approved the work.

A manager can reject a pending task back to Working. Tasks with a real past due date become Overdue automatically. Pomas also raises active-task priority as a due date approaches without lowering a manually higher priority.

## Claim and submit work

Open an unassigned task and choose **Take task** to assign it to yourself. When a task is assigned to you, use **Submit** to open the desktop work-submission panel.

Enter a required work description and optionally select files from your computer. Pomas stores selected files privately. Once submitted, the task moves to Pending Review. Approved and pending-review task details show the latest submitted files to authorized project members.

## My Tasks and project map

**My tasks** groups your assigned tasks under each relevant project. The Project Map presents a selected project and its tasks visually; use the project selector at the top to change the map.

## GitHub repositories

When creating or editing a project, you can either link an existing GitHub repository URL or create a private repository through the configured GitHub App organization connection. This connection is optional. Pomas does not automatically push submitted files to GitHub.

## Appearance and navigation

Use the profile menu for Settings, including light/dark theme preference and GitHub connection settings. Collapse or expand the project sidebar with the sidebar control; `Ctrl+B` also toggles it on desktop.
