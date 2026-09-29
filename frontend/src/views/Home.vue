<template>
  <div class="pms-shell" :class="{ 'is-collapsed': sidebarCollapsed }">
    <aside class="sidebar">
      <div class="sidebar-scroll-area">
        <div class="brand"><span class="brand-mark"><img src="/Pomas-Logo.png" alt="" /></span><div><strong>Pomas</strong><small>Project workspace</small></div></div>
        <nav class="primary-nav" aria-label="Primary navigation">
          <button class="nav-item" :class="{ active: activeView === 'projects' }" title="All Projects" @click="showAllProjects"><span class="nav-icon">▦</span><span class="nav-label">All Projects</span></button>
          <button class="nav-item" :class="{ active: activeView === 'my-tasks' }" title="My tasks" @click="showMyTasks"><span class="nav-icon">✓</span><span class="nav-label">My tasks</span><small>{{ myTasks.length }}</small></button>
          <button class="nav-item" :class="{ active: activeView === 'project-map' }" title="Project map" @click="showProjectMap"><span class="nav-icon">◎</span><span class="nav-label">Project map</span></button>
        </nav>
        <div class="sidebar-section">
          <div class="section-label"><span>{{ sidebarCollapsed ? "-------" : "Your projects" }}</span><span v-if="!sidebarCollapsed">{{ projects.length }}</span></div>
          <div v-if="loading" class="project-skeleton" />
          <button v-for="project in projects" :key="project.name" class="project-link" :class="{ active: selectedProject === project.name }" :title="project.project_name" @click="selectProject(project.name)"><span class="project-avatar"><img v-if="project.logo" :src="project.logo" alt="" /><span v-else>{{ initials(project.project_name) }}</span></span><span class="project-link-copy"><strong>{{ project.project_name }}</strong><small>{{ project.status }} · {{ Math.round(project.percent_complete || 0) }}%</small></span></button>
        </div>
      </div>
      <button class="sidebar-collapse" type="button" :aria-label="sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'" :title="sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'" @click="toggleSidebar"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg><span>{{ sidebarCollapsed ? "Expand" : "Collapse" }}</span></button>
      <AccountMenu v-if="session" :session="session" variant="sidebar" @menu-change="handleAccountMenuChange" />
    </aside>

    <main class="workspace" :class="{ 'workspace--board': activeView === 'board' }">
      <header class="topbar">
        <div><p class="eyebrow">Workspace</p><h1>{{ pageTitle }}</h1></div>
        <div class="topbar-actions">
          <ProjectActionsMenu v-if="board?.project.can_manage_team && activeView === 'board' && board" :project="board.project" @changed="refreshWorkspace" @deleted="handleProjectDeleted" />
          <button class="refresh-button" type="button" :disabled="loading || refreshing" @click="refreshWorkspace"><svg :class="{ spinning: refreshing }" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.3 5.7" /><path d="M20 4v7h-7" /></svg><span>{{ refreshing ? "Refreshing…" : "Refresh" }}</span></button>
          <AccountMenu v-if="session" :session="session" variant="mobile" />
          <label class="mobile-project-picker"><span class="sr-only">Choose project</span><select :value="selectedProject || ''" @change="selectProject(($event.target as HTMLSelectElement).value)"><option value="">All Projects</option><option v-for="project in projects" :key="project.name" :value="project.name">{{ project.project_name }}</option></select></label>
          <div v-if="activeView !== 'project-map'" ref="filterMenu" class="filter-menu">
            <button class="secondary-button filter-button" :class="{ 'is-active': filterActive }" type="button" aria-haspopup="true" :aria-expanded="filterOpen" @click.stop="filterOpen = !filterOpen"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18l-7 8v6l-4-2v-4z" /></svg><span>Filter</span><b v-if="filterActive" class="filter-badge">{{ currentFilterLabel }}</b></button>
            <Transition name="filter-pop">
              <div v-if="filterOpen" class="filter-popover" role="radiogroup" :aria-label="filterTitle">
                <p class="filter-title">{{ filterTitle }}</p>
                <label v-for="option in currentFilterOptions" :key="option.value" class="filter-option"><input :checked="currentFilterValue === option.value" type="radio" name="workspace-filter" :value="option.value" @change="applyFilter(option.value)" /><span class="filter-radio" /><span>{{ option.label }}</span><small v-if="option.count !== undefined">{{ option.count }}</small></label>
              </div>
            </Transition>
          </div>
          <button v-if="session?.can_create_projects && activeView === 'projects'" class="primary-button new-task-button" type="button" @click="projectDrawerOpen = true">+ New project</button>
          <button v-else-if="board?.project.can_manage && activeView === 'board'" class="primary-button new-task-button" type="button" @click="openTaskCreate()">+ New task</button>
        </div>
      </header>

      <section v-if="loading" class="center-state"><span class="spinner" /><p>Loading your workspace…</p></section>
      <section v-else-if="error" class="center-state error-state"><div class="state-icon">!</div><h2>We could not load Pomas</h2><p>{{ error }}</p><button class="secondary-button" @click="loadWorkspace">Try again</button></section>
      <section v-else-if="!projects.length" class="center-state empty-workspace-state"><div class="state-icon">＋</div><h2>{{ activeView === 'my-tasks' ? 'No tasks yet' : 'No projects yet' }}</h2><p>{{ activeView === 'my-tasks' ? 'Tasks assigned to you will appear here.' : 'Create a project or ask a Project Owner to add you as a member.' }}</p></section>

      <section v-else-if="activeView === 'projects'" class="projects-overview">
        <header class="overview-header"><div><p class="eyebrow">Portfolio</p><h2>Project portfolio</h2></div><p>{{ projects.length }} {{ projects.length === 1 ? "project" : "projects" }}</p></header>
        <div class="project-grid">
          <button v-for="project in visibleProjects" :key="project.name" class="project-tile" @click="selectProject(project.name)">
            <span class="project-tile-mark"><img v-if="project.logo" :src="project.logo" alt="" /><span v-else>{{ initials(project.project_name) }}</span></span><span class="project-tile-copy"><small>{{ project.status }}</small><strong>{{ project.project_name }}</strong><span>{{ formatDate(project.expected_start_date) }} — {{ formatDate(project.expected_end_date) }}</span><span class="unassigned-count">{{ project.unassigned_task_count }} unassigned · {{ project.task_count }} tasks</span></span><b>{{ Math.round(project.percent_complete || 0) }}%</b><span class="project-tile-progress"><i :style="{ width: `${Math.min(project.percent_complete || 0, 100)}%` }" /></span>
          </button>
        </div>
      </section>

      <section v-else-if="activeView === 'my-tasks'" class="my-tasks-view">
        <header class="overview-header"><div><p class="eyebrow">Personal queue</p><h2>Tasks assigned to you</h2></div><p>{{ visibleMyTasks.length }} {{ visibleMyTasks.length === 1 ? "task" : "tasks" }}</p></header>
        <div v-if="visibleMyTasks.length" class="my-project-groups">
          <article v-for="project in myTaskProjectGroups" :key="project.name" class="my-project-group"><header class="my-project-header"><div><p>Project</p><h3>{{ project.label }}</h3></div><span>{{ project.taskCount }} {{ project.taskCount === 1 ? "task" : "tasks" }}</span></header><div class="my-project-task-grid"><button v-for="task in project.tasks" :key="task.name" class="task-card my-task-card" @click="openTaskDetails(task.name)"><div class="task-card-top"><span v-if="task.priority" :class="['priority', `priority-${task.priority.toLowerCase()}`]">{{ task.priority }}</span><span class="task-id">{{ task.name }}</span><span v-if="task.status === 'Completed'" class="completed-badge">Completed</span><span v-if="task.is_milestone" class="milestone-star" title="Milestone" aria-label="Milestone">★</span></div><h3>{{ task.subject }}</h3><div class="task-meta"><span>{{ task.status }}</span><span v-if="task.exp_end_date">◷ {{ formatDate(task.exp_end_date) }}</span><span v-if="task.progress">{{ task.progress }}%</span></div></button></div></article>
        </div>
        <div v-else class="center-state compact-state"><div class="state-icon">✓</div><h2>No matching tasks</h2><p>Assigned tasks will appear here.</p></div>
      </section>

      <ProjectMap v-else-if="activeView === 'project-map' && board" :board="board" :projects="projects" @select-project="selectMapProject" @open-board="openBoardFromMap" @open-task="openTaskDetails" />

      <template v-else-if="board">
        <section class="project-summary"><div class="summary-item"><span>Status</span><strong><i class="status-dot" />{{ board.project.status }}</strong></div><div class="summary-item"><span>Progress</span><strong>{{ Math.round(board.project.percent_complete || 0) }}%</strong></div><div class="summary-item"><span>Due date</span><strong>{{ formatDate(board.project.expected_end_date) }}</strong></div><div class="summary-item"><span>Client</span><strong>{{ board.project.customer || "Not set" }}</strong></div><div class="progress-track" aria-label="Project progress"><span :style="{ width: `${Math.min(board.project.percent_complete || 0, 100)}%` }" /></div><button class="secondary-button summary-map-button" type="button" @click="showProjectMap">◎ Project map</button></section>
        <section class="board" aria-label="Project Kanban board">
          <article v-for="column in visibleColumns" :key="column.status" class="board-column" :class="{ 'is-column-collapsed': collapsedColumns.has(column.status) }">
            <header class="column-header"><span :class="['column-indicator', statusClass(column.status)]" /><h2>{{ column.status }}</h2><span class="task-count">{{ column.tasks.length }}</span><div class="column-menu-wrap"><button class="column-menu" type="button" :aria-expanded="openColumnMenu === column.status" aria-label="Column options" @click.stop="toggleColumnMenu(column.status)">•••</button><div v-if="openColumnMenu === column.status" class="column-popover"><button v-if="board?.project.can_manage && ['Open'].includes(column.status)" @click="openTaskCreate()">Add task here</button><button @click="setColumnSort(column.status, 'newest')">Sort by newest</button><button @click="setColumnSort(column.status, 'due')">Sort by due date</button><button @click="setColumnSort(column.status, 'priority')">Sort by priority</button><button @click="toggleColumnCollapse(column.status)">{{ collapsedColumns.has(column.status) ? "Expand column" : "Collapse column" }}</button></div></div></header>
            <div v-if="!collapsedColumns.has(column.status)" class="card-stack">
              <button v-for="task in column.tasks" :key="task.name" class="task-card" @click="openTaskDetails(task.name)"><div class="task-card-top"><span v-if="task.priority" :class="['priority', `priority-${task.priority.toLowerCase()}`]">{{ task.priority }}</span><span class="task-id">{{ task.name }}</span><span v-if="task.is_milestone" class="milestone-star" title="Milestone" aria-label="Milestone">★</span></div><h3>{{ task.subject }}</h3><div class="task-meta"><span v-if="task.exp_end_date">◷ {{ formatDate(task.exp_end_date) }}</span><span v-if="task.progress">{{ task.progress }}%</span><span v-if="!task.assignees.length">Unassigned</span></div><div v-if="task.assignees.length" class="assignees"><span v-for="assignee in task.assignees.slice(0,3)" :key="assignee" class="mini-avatar" :title="assignee">{{ initials(assignee) }}</span></div></button>
              <div v-if="!column.tasks.length" class="empty-column">No tasks here</div>
            </div>
          </article>
        </section>
      </template>
    </main>

    <TaskCreateDrawer v-if="taskDrawerOpen && board && selectedProject" :project="selectedProject" :project-name="board.project.project_name" :project-due-date="board.project.expected_end_date" @close="closeTaskCreate" @created="handleTaskCreated" />
    <ProjectCreateDrawer v-if="projectDrawerOpen" @close="projectDrawerOpen = false" @created="handleProjectCreated" @open="openCreatedProject" />
    <TaskDetailDrawer v-if="detailTask" :task="detailTask" @close="detailTask = null" @taken="handleTaskTaken" @submit="openWorkSubmission" @edit="openTaskEdit" @updated="handleTaskUpdated" @deleted="handleTaskDeleted" />
    <TaskEditDrawer v-if="editTask" :task="editTask" @close="editTask = null" @updated="handleTaskUpdated" />
    <WorkSubmissionDrawer v-if="submissionTask" :task="submissionTask" @close="submissionTask = null" @submitted="handleTaskUpdated" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import AccountMenu from "../components/AccountMenu.vue"
import ProjectCreateDrawer from "../components/ProjectCreateDrawer.vue"
import ProjectActionsMenu from "../components/ProjectActionsMenu.vue"
import ProjectMap from "../components/ProjectMap.vue"
import TaskCreateDrawer from "../components/TaskCreateDrawer.vue"
import TaskDetailDrawer from "../components/TaskDetailDrawer.vue"
import TaskEditDrawer from "../components/TaskEditDrawer.vue"
import WorkSubmissionDrawer from "../components/WorkSubmissionDrawer.vue"
import { callPms, type BoardData, type CreateProjectResult, type CreateTaskResult, type PmsSession, type ProjectSummary, type TaskCard, type TaskDetails } from "../services/api"

const SIDEBAR_KEY = "pomas-sidebar-collapsed"
const sidebarCollapsed = ref(readCollapsed())
let restoreSidebarAfterAccount = false
const session = ref<PmsSession | null>(null)
const projects = ref<ProjectSummary[]>([])
const board = ref<BoardData | null>(null)
const myTasks = ref<TaskCard[]>([])
const selectedProject = ref<string | null>(null)
const myTasksActive = ref(false)
const mapActive = ref(false)
const loading = ref(true)
const refreshing = ref(false)
const error = ref("")
const taskDrawerOpen = ref(false)
const projectDrawerOpen = ref(false)
const detailTask = ref<string | null>(null)
const editTask = ref<TaskDetails | null>(null)
const submissionTask = ref<TaskDetails | null>(null)

type TaskFilter = "all" | "assigned" | "unassigned"
type MyTaskFilter = "all" | "Open" | "Working" | "Pending Review" | "Overdue" | "Completed"
type ProjectSort = "modified" | "progress-high" | "progress-low" | "due-soon" | "unassigned"
type ColumnSort = "newest" | "due" | "priority"
const taskFilter = ref<TaskFilter>("all")
const myTaskFilter = ref<MyTaskFilter>("all")
const projectSort = ref<ProjectSort>("modified")
const filterOpen = ref(false)
const filterMenu = ref<HTMLElement | null>(null)
const openColumnMenu = ref<string | null>(null)
const columnSorts = reactive<Record<string, ColumnSort>>({})
const collapsedColumns = reactive(new Set<string>())

const activeView = computed(() => mapActive.value ? "project-map" : selectedProject.value ? "board" : myTasksActive.value ? "my-tasks" : "projects")
const pageTitle = computed(() => activeView.value === "my-tasks" ? "My Tasks" : activeView.value === "project-map" ? "Project Map" : board.value?.project.project_name || "All Projects")
const allTasks = computed(() => board.value?.columns.flatMap((column) => column.tasks) ?? [])
const visibleProjects = computed(() => [...projects.value].sort((a, b) => {
  if (projectSort.value === "progress-high") return (b.percent_complete || 0) - (a.percent_complete || 0)
  if (projectSort.value === "progress-low") return (a.percent_complete || 0) - (b.percent_complete || 0)
  if (projectSort.value === "due-soon") return dateValue(a.expected_end_date) - dateValue(b.expected_end_date)
  if (projectSort.value === "unassigned") return (b.unassigned_task_count || 0) - (a.unassigned_task_count || 0)
  return new Date(b.modified).getTime() - new Date(a.modified).getTime()
}))
const visibleMyTasks = computed(() => myTasks.value.filter((task) => myTaskFilter.value === "all" || task.status === myTaskFilter.value))
const myTaskProjectGroups = computed(() => {
  const groups = new Map<string, { name: string; label: string; tasks: TaskCard[] }>()
  for (const task of visibleMyTasks.value) {
    const name = task.project || task.project_name || "unknown-project"
    const group = groups.get(name) || { name, label: task.project_name || name, tasks: [] }
    group.tasks.push(task)
    groups.set(name, group)
  }
  return [...groups.values()].sort((a, b) => a.label.localeCompare(b.label)).map((group) => ({
    ...group,
    taskCount: group.tasks.length,
    tasks: sortColumn(group.tasks, "newest"),
  }))
})
const boardFilterOptions = computed(() => { const assigned = allTasks.value.filter((task) => task.assignees.length).length; return [{ value: "all", label: "All tasks", count: allTasks.value.length }, { value: "assigned", label: "Assigned", count: assigned }, { value: "unassigned", label: "Unassigned", count: allTasks.value.length - assigned }] })
const projectFilterOptions = [{ value: "modified", label: "Recently updated" }, { value: "progress-high", label: "Progress: high to low" }, { value: "progress-low", label: "Progress: low to high" }, { value: "due-soon", label: "Due date: soonest" }, { value: "unassigned", label: "Most unassigned tasks" }]
const myTaskFilterOptions = computed(() => ["all", "Open", "Working", "Pending Review", "Overdue", "Completed"].map((value) => ({ value, label: value === "all" ? "All tasks" : value, count: value === "all" ? myTasks.value.length : myTasks.value.filter((task) => task.status === value).length })))
const currentFilterOptions = computed(() => activeView.value === "projects" ? projectFilterOptions : activeView.value === "my-tasks" ? myTaskFilterOptions.value : boardFilterOptions.value)
const currentFilterValue = computed(() => activeView.value === "projects" ? projectSort.value : activeView.value === "my-tasks" ? myTaskFilter.value : taskFilter.value)
const currentFilterLabel = computed(() => currentFilterOptions.value.find((option) => option.value === currentFilterValue.value)?.label || "")
const filterActive = computed(() => activeView.value === "projects" ? projectSort.value !== "modified" : activeView.value === "my-tasks" ? myTaskFilter.value !== "all" : taskFilter.value !== "all")
const filterTitle = computed(() => activeView.value === "projects" ? "Sort projects" : "Show tasks")
const visibleColumns = computed(() => (board.value?.columns || []).map((column) => ({ ...column, tasks: sortColumn(column.tasks.filter((task) => taskFilter.value === "all" || (taskFilter.value === "assigned") === Boolean(task.assignees.length)), columnSorts[column.status] || "newest") })))

onMounted(() => { loadWorkspace(); document.addEventListener("click", closeFloatingMenus); document.addEventListener("keydown", onEscape) })
onBeforeUnmount(() => { document.removeEventListener("click", closeFloatingMenus); document.removeEventListener("keydown", onEscape) })
function closeFloatingMenus(event: MouseEvent) { if (filterOpen.value && filterMenu.value && !filterMenu.value.contains(event.target as Node)) filterOpen.value = false; openColumnMenu.value = null }
function onEscape(event: KeyboardEvent) { if (event.ctrlKey && event.key.toLowerCase() === "b") { event.preventDefault(); toggleSidebar(); return } if (event.key === "Escape") { filterOpen.value = false; openColumnMenu.value = null } }

async function loadWorkspace() { loading.value = true; error.value = ""; try { const [sessionData, projectData, myTaskData] = await Promise.all([callPms<PmsSession>("pms.api.get_session"), callPms<ProjectSummary[]>("pms.api.get_projects"), callPms<TaskCard[]>("pms.api.get_my_tasks")]); session.value = sessionData; projects.value = projectData; myTasks.value = myTaskData } catch (reason) { error.value = reason instanceof Error ? reason.message : "Unable to load the workspace." } finally { loading.value = false } }
async function selectProject(projectName: string) { if (!projectName) { showAllProjects(); return } selectedProject.value = projectName; myTasksActive.value = false; mapActive.value = false; error.value = ""; try { board.value = await callPms<BoardData>("pms.api.get_board", { project: projectName }) } catch (reason) { error.value = reason instanceof Error ? reason.message : "Unable to load this project." } }
async function loadMyTasks() { myTasks.value = await callPms<TaskCard[]>("pms.api.get_my_tasks") }
async function showMyTasks() { selectedProject.value = null; board.value = null; myTasksActive.value = true; mapActive.value = false; filterOpen.value = false; error.value = ""; try { await loadMyTasks() } catch (reason) { error.value = reason instanceof Error ? reason.message : "Unable to load your tasks." } }
async function refreshWorkspace() { if (refreshing.value) return; refreshing.value = true; error.value = ""; try { const [sessionData, projectData, myTaskData, boardData] = await Promise.all([callPms<PmsSession>("pms.api.get_session"), callPms<ProjectSummary[]>("pms.api.get_projects"), callPms<TaskCard[]>("pms.api.get_my_tasks"), ["board", "project-map"].includes(activeView.value) && selectedProject.value ? callPms<BoardData>("pms.api.get_board", { project: selectedProject.value }) : Promise.resolve(null)]); session.value = sessionData; projects.value = projectData; myTasks.value = myTaskData; if (boardData) board.value = boardData } catch (reason) { error.value = reason instanceof Error ? reason.message : "Unable to refresh the workspace." } finally { refreshing.value = false } }
function showAllProjects() { filterOpen.value = false; selectedProject.value = null; myTasksActive.value = false; mapActive.value = false; board.value = null; error.value = "" }
async function showProjectMap() { filterOpen.value = false; myTasksActive.value = false; mapActive.value = true; error.value = ""; const projectName = selectedProject.value || projects.value[0]?.name; if (!projectName) return; selectedProject.value = projectName; if (board.value?.project.name === projectName) return; try { board.value = await callPms<BoardData>("pms.api.get_board", { project: projectName }) } catch (reason) { error.value = reason instanceof Error ? reason.message : "Unable to load the project map." } }
async function selectMapProject(projectName: string) { if (!projectName) return; selectedProject.value = projectName; mapActive.value = true; error.value = ""; try { board.value = await callPms<BoardData>("pms.api.get_board", { project: projectName }) } catch (reason) { error.value = reason instanceof Error ? reason.message : "Unable to load the project map." } }
function openBoardFromMap() { mapActive.value = false }
function applyFilter(value: string) { if (activeView.value === "projects") projectSort.value = value as ProjectSort; else if (activeView.value === "my-tasks") myTaskFilter.value = value as MyTaskFilter; else taskFilter.value = value as TaskFilter; filterOpen.value = false }
function openTaskCreate() { taskDrawerOpen.value = true; openColumnMenu.value = null }
function closeTaskCreate() { taskDrawerOpen.value = false }
async function handleProjectCreated() { const projectData = await callPms<ProjectSummary[]>("pms.api.get_projects"); projects.value = projectData }
async function handleTaskCreated(_task: CreateTaskResult) { await refreshWorkspace() }
async function openCreatedProject(project: CreateProjectResult) { projectDrawerOpen.value = false; await selectProject(project.name) }
function openTaskDetails(task: string) { detailTask.value = task }
function openTaskEdit(task: TaskDetails) { detailTask.value = null; editTask.value = task }
async function handleTaskUpdated(_task: TaskDetails) { detailTask.value = null; editTask.value = null; await refreshWorkspace() }
async function handleTaskDeleted(_task: string) { detailTask.value = null; await refreshWorkspace() }
async function handleProjectDeleted(projectName: string) { if (selectedProject.value === projectName) showAllProjects(); await refreshWorkspace() }
function openWorkSubmission(task: TaskDetails) { detailTask.value = null; submissionTask.value = task }
async function handleTaskTaken(_task: TaskDetails) { await Promise.all([refreshWorkspace(), loadMyTasks()]) }
function toggleColumnMenu(status: string) { openColumnMenu.value = openColumnMenu.value === status ? null : status }
function setColumnSort(status: string, sort: ColumnSort) { columnSorts[status] = sort; openColumnMenu.value = null }
function toggleColumnCollapse(status: string) { if (collapsedColumns.has(status)) collapsedColumns.delete(status); else collapsedColumns.add(status); openColumnMenu.value = null }
function sortColumn(tasks: TaskCard[], sort: ColumnSort) { const result = [...tasks]; if (sort === "due") return result.sort((a,b) => dateValue(a.exp_end_date) - dateValue(b.exp_end_date)); if (sort === "priority") { const rank: Record<string,number> = { Urgent: 4, High: 3, Medium: 2, Low: 1 }; return result.sort((a,b) => (rank[b.priority] || 0) - (rank[a.priority] || 0)) } return result.sort((a,b) => new Date(b.modified).getTime() - new Date(a.modified).getTime()) }
function dateValue(value?: string) { return value ? new Date(`${value}T00:00:00`).getTime() : Number.MAX_SAFE_INTEGER }
function readCollapsed() { try { return window.localStorage.getItem(SIDEBAR_KEY) === "1" } catch { return false } }
function toggleSidebar() { restoreSidebarAfterAccount = false; sidebarCollapsed.value = !sidebarCollapsed.value; try { window.localStorage.setItem(SIDEBAR_KEY, sidebarCollapsed.value ? "1" : "0") } catch { /* unavailable */ } }
function handleAccountMenuChange(open: boolean) { if (open && sidebarCollapsed.value) { restoreSidebarAfterAccount = true; sidebarCollapsed.value = false; return } if (!open && restoreSidebarAfterAccount) { restoreSidebarAfterAccount = false; sidebarCollapsed.value = true } }
function initials(value: string) { return value.split(/[@.\s]+/).filter(Boolean).slice(0,2).map((part) => part[0]?.toUpperCase()).join("") }
function formatDate(value?: string) { if (!value) return "Not set"; return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(`${value}T00:00:00`)) }
function statusClass(status: string) { return `status-${status.toLowerCase().replace(/\s+/g, "-")}` }
</script>
