export type PmsSession = {
  user: string
  full_name: string
  user_image?: string | null
  roles: string[]
  is_administrator: boolean
  can_create_tasks: boolean
  can_manage_github: boolean
  can_create_projects: boolean
}

export type TaskFormMember = {
  name: string
  full_name?: string
  user_image?: string | null
}

export type TaskFormOptions = {
  statuses: string[]
  priorities: string[]
  members: TaskFormMember[]
}

export type CreateTaskResult = {
  name: string
  subject: string
  status: string
  priority: string
  assignees: string[]
}

export type GitHubProjectLink = {
  repository_url: string
  repository_owner: string
  repository_name: string
  connection_mode: "Existing repository" | "Created by Pomas"
  connection_status: "Unverified" | "Connected" | "Failed"
}

export type CreateProjectResult = {
  name: string
  project_name: string
  github?: GitHubProjectLink | null
}

export type ProjectSummary = {
  name: string
  project_name: string
  status: string
  percent_complete: number
  expected_start_date?: string
  expected_end_date?: string
  modified: string
  github?: GitHubProjectLink | null
  logo?: string | null
  task_count: number
  unassigned_task_count: number
  customer?: string | null
  project_role?: "Owner" | "Project Manager" | "Member" | null
  can_manage?: boolean
  can_manage_team?: boolean
}

export type TaskCard = {
  name: string
  subject: string
  project?: string
  project_name?: string
  status: string
  priority: string
  exp_end_date?: string
  progress: number
  is_milestone?: boolean | number
  assignees: string[]
  modified: string
}

export type SubmittedWorkFile = {
  name: string
  file_name: string
  repository_path: string
  file?: string
  file_size?: number
}

export type SubmittedWork = {
  name: string
  submitted_by: string
  submitted_on: string
  description: string
  files: SubmittedWorkFile[]
}

export type TaskDetails = TaskCard & {
  exp_start_date?: string
  expected_time?: number
  description?: string
  is_milestone?: boolean | number
  can_take: boolean
  can_submit: boolean
  can_edit: boolean
  can_delete: boolean
  can_review: boolean
  submissions: SubmittedWork[]
}

export type WorkSubmissionFile = {
  file_name: string
  repository_path: string
}

export type WorkSubmissionResult = {
  name: string
  task: string
  submitted_on: string
  file_count: number
  status: string
}

export type BoardColumn = {
  status: string
  tasks: TaskCard[]
}

export type BoardData = {
  project: ProjectSummary
  columns: BoardColumn[]
}

declare global {
  interface Window {
    csrf_token?: string
  }
}

export async function callPms<T>(method: string, args: Record<string, unknown> = {}): Promise<T> {
  const response = await fetch(`/api/method/${method}`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json; charset=utf-8",
      "X-Frappe-Site-Name": window.location.hostname,
      ...(window.csrf_token ? { "X-Frappe-CSRF-Token": window.csrf_token } : {}),
    },
    body: JSON.stringify(args),
  })

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const serverMessages = payload._server_messages ? JSON.parse(payload._server_messages) : []
    const message = serverMessages.length ? JSON.parse(serverMessages[0]).message : payload.message
    throw new Error(message || "Something went wrong. Please try again.")
  }
  return payload.message as T
}

export async function uploadPms<T>(method: string, formData: FormData): Promise<T> {
  const response = await fetch(`/api/method/${method}`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "X-Frappe-Site-Name": window.location.hostname,
      ...(window.csrf_token ? { "X-Frappe-CSRF-Token": window.csrf_token } : {}),
    },
    body: formData,
  })

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const serverMessages = payload._server_messages ? JSON.parse(payload._server_messages) : []
    const message = serverMessages.length ? JSON.parse(serverMessages[0]).message : payload.message
    throw new Error(message || "Something went wrong. Please try again.")
  }
  return payload.message as T
}
