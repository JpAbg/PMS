<template>
  <section class="project-map-view">
    <header class="map-toolbar">
      <div>
        <p class="eyebrow">Project map</p>
        <h2>Explore the work around this project</h2>
        <span>Open a task node to view its details, assignment, and submission actions.</span>
      </div>
      <div class="map-toolbar-actions">
        <label class="map-project-picker"><span>Project</span><PomasSelect :model-value="board.project.name" label="Project" :options="projects.map((project) => ({ value: project.name, label: project.project_name }))" @update:model-value="emit('select-project', $event)" /></label>
        <button class="map-board-button" type="button" @click="emit('open-board')">View board</button>
      </div>
    </header>

    <div class="map-legend" aria-label="Project map legend">
      <span><i class="legend-open" />Open</span>
      <span><i class="legend-working" />Working</span>
      <span><i class="legend-review" />Pending review</span>
      <span><i class="legend-overdue" />Overdue</span>
      <span><i class="legend-completed" />Completed</span>
      <span><i class="legend-milestone" />Milestone</span>
    </div>

    <div class="map-scroll">
      <div class="map-canvas" :class="{ 'is-empty': !nodes.length }">
        <svg v-if="nodes.length" class="map-links" viewBox="0 0 1000 640" aria-hidden="true" preserveAspectRatio="none">
          <line v-for="node in nodes" :key="node.task.name" x1="500" y1="320" :x2="node.x" :y2="node.y" />
        </svg>

        <button class="project-map-node" type="button" @click="emit('open-board')">
          <small>{{ board.project.status }}</small>
          <strong>{{ board.project.project_name }}</strong>
          <span>{{ Math.round(board.project.percent_complete || 0) }}% complete</span>
          <i><b :style="{ width: `${Math.min(board.project.percent_complete || 0, 100)}%` }" /></i>
        </button>

        <button
          v-for="node in nodes"
          :key="node.task.name"
          class="task-map-node"
          :class="[statusNodeClass(node.task.status), { 'is-milestone': node.task.is_milestone }]"
          :style="nodeStyle(node)"
          type="button"
          @click="emit('open-task', node.task.name)"
        >
          <span class="map-node-status">{{ node.task.is_milestone ? "Milestone" : node.task.status }}</span>
          <strong>{{ node.task.subject }}</strong>
          <small>{{ node.task.assignees.length ? node.task.assignees.length + " assigned" : "Unassigned" }}</small>
          <span v-if="node.task.assignees.length" class="map-node-avatars">
            <i v-for="assignee in node.task.assignees.slice(0, 3)" :key="assignee" :title="assignee">{{ initials(assignee) }}</i>
          </span>
        </button>

        <div v-if="!nodes.length" class="map-empty">
          <strong>No tasks in this project yet</strong>
          <span>The project node will connect to tasks as they are created.</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue"
import PomasSelect from "./PomasSelect.vue"
import type { BoardData, ProjectSummary, TaskCard } from "../services/api"

type MapNode = {
  task: TaskCard
  x: number
  y: number
}

const props = defineProps<{
  board: BoardData
  projects: ProjectSummary[]
}>()

const emit = defineEmits<{
  (event: "select-project", project: string): void
  (event: "open-board"): void
  (event: "open-task", task: string): void
}>()

const tasks = computed(() => props.board.columns.flatMap((column) => column.tasks))
const nodes = computed<MapNode[]>(() => {
  const taskList = tasks.value
  if (!taskList.length) return []

  const innerCount = taskList.length > 9 ? Math.ceil(taskList.length / 2) : taskList.length
  return taskList.map((task, index) => {
    const outer = index >= innerCount
    const ringIndex = outer ? index - innerCount : index
    const ringCount = outer ? taskList.length - innerCount : innerCount
    const angle = (-Math.PI / 2) + (Math.PI * 2 * ringIndex) / Math.max(ringCount, 1) + (outer ? Math.PI / Math.max(ringCount, 1) : 0)
    const radiusX = outer ? 420 : taskList.length > 9 ? 255 : 365
    const radiusY = outer ? 265 : taskList.length > 9 ? 165 : 225
    return {
      task,
      x: 500 + Math.cos(angle) * radiusX,
      y: 320 + Math.sin(angle) * radiusY,
    }
  })
})

function nodeStyle(node: MapNode) {
  return {
    left: `${node.x / 10}%`,
    top: `${node.y / 6.4}%`,
  }
}

function statusNodeClass(status: string) {
  return `map-status-${status.toLowerCase().replace(/\s+/g, "-")}`
}

function initials(value: string) {
  return value
    .split(/[@.\s]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("")
}
</script>

<style scoped>
.project-map-view{padding:8px 0 28px}.map-toolbar{display:flex;align-items:end;justify-content:space-between;gap:24px;margin:10px 0 14px}.map-toolbar h2{margin:0;color:var(--c-ink);font-size:22px;letter-spacing:-.03em}.map-toolbar>div:first-child>span{display:block;max-width:590px;margin-top:7px;color:var(--muted);font-size:11px;line-height:1.55}.map-toolbar-actions{display:flex;align-items:end;gap:9px}.map-project-picker{display:grid;gap:5px;color:var(--muted);font-size:9px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.map-project-picker :deep(.pomas-select){min-width:220px}.map-project-picker :deep(.select-trigger){min-height:40px;border-radius:9px;text-transform:none;letter-spacing:0}.map-board-button{height:40px;padding:0 14px;border:1px solid var(--c-violet);border-radius:9px;background:var(--c-violet);color:white;font-size:11px;font-weight:800;cursor:pointer}.map-legend{display:flex;flex-wrap:wrap;gap:8px 16px;margin:0 0 12px;padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:white;color:var(--muted);font-size:9px;font-weight:700}.map-legend span{display:flex;align-items:center;gap:6px}.map-legend i{width:8px;height:8px;border-radius:50%;background:var(--faint)}.map-legend .legend-working{background:#3b9cff}.map-legend .legend-review{background:#f2a93b}.map-legend .legend-overdue{background:#e5484d}.map-legend .legend-completed{background:#3eb281}.map-legend .legend-milestone{border-radius:2px;background:var(--c-violet);transform:rotate(45deg)}.map-scroll{overflow:auto;border:1px solid var(--line);border-radius:16px;background:radial-gradient(circle at 50% 50%,color-mix(in srgb,var(--c-lavender) 72%,white),white 55%);box-shadow:0 8px 30px rgba(12,9,20,.05)}.map-canvas{position:relative;min-width:850px;height:max(620px,calc(100vh - 240px));min-height:620px;overflow:hidden;background-image:radial-gradient(circle,color-mix(in srgb,var(--faint) 32%,transparent) 1px,transparent 1px);background-size:24px 24px}.map-links{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}.map-links line{stroke:color-mix(in srgb,var(--c-violet) 25%,var(--line));stroke-width:1.4;stroke-dasharray:5 5;vector-effect:non-scaling-stroke}.project-map-node,.task-map-node{position:absolute;z-index:2;transform:translate(-50%,-50%);cursor:pointer;transition:transform .16s,border-color .16s,box-shadow .16s}.project-map-node:hover,.task-map-node:hover{transform:translate(-50%,-50%) scale(1.04)}.project-map-node{top:50%;left:50%;width:190px;min-height:128px;display:grid;align-content:center;gap:7px;padding:18px;border:2px solid var(--c-violet);border-radius:26px;background:var(--c-ink);color:white;text-align:center;box-shadow:0 18px 45px color-mix(in srgb,var(--c-violet) 30%,transparent)}.project-map-node small{color:var(--c-orchid);font-size:8px;font-weight:850;letter-spacing:.1em;text-transform:uppercase}.project-map-node strong{font-size:14px;line-height:1.3}.project-map-node span{color:var(--sb-muted);font-size:9px}.project-map-node>i{height:4px;border-radius:4px;background:var(--sb-line);overflow:hidden}.project-map-node>i b{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--c-violet),var(--c-orchid))}.task-map-node{width:164px;min-height:94px;display:grid;align-content:center;gap:6px;padding:12px 13px;border:1px solid var(--line);border-top:3px solid var(--node-color,var(--faint));border-radius:13px;background:white;color:var(--text-2);text-align:left;box-shadow:0 8px 22px rgba(12,9,20,.09)}.task-map-node:hover{border-color:var(--node-color,var(--c-violet));box-shadow:0 13px 28px rgba(12,9,20,.15)}.task-map-node.is-milestone{border-radius:7px}.task-map-node.is-milestone::after{content:"◆";position:absolute;top:8px;right:9px;color:var(--c-violet);font-size:9px}.map-node-status{color:var(--node-color,var(--muted));font-size:8px;font-weight:850;letter-spacing:.07em;text-transform:uppercase}.task-map-node strong{padding-right:10px;color:var(--c-ink);font-size:11px;line-height:1.35}.task-map-node small{color:var(--faint);font-size:8px;font-weight:700}.map-node-avatars{display:flex;justify-content:flex-end;margin-top:-20px}.map-node-avatars i{width:22px;height:22px;display:grid;place-items:center;margin-left:-5px;border:2px solid white;border-radius:50%;background:var(--c-lavender);color:var(--c-plum);font-size:7px;font-style:normal;font-weight:850}.map-status-working{--node-color:#3b9cff}.map-status-pending-review{--node-color:#f2a93b}.map-status-overdue{--node-color:#e5484d}.map-status-completed{--node-color:#3eb281}.map-empty{position:absolute;top:calc(50% + 92px);left:50%;display:grid;gap:4px;transform:translateX(-50%);color:var(--muted);font-size:10px;text-align:center}.map-empty strong{color:var(--text-2);font-size:12px}[data-theme=dark] .map-toolbar h2,[data-theme=dark] .task-map-node strong{color:var(--d-title)}[data-theme=dark] .map-project-picker :deep(.select-trigger),[data-theme=dark] .map-legend,[data-theme=dark] .task-map-node{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .map-scroll{border-color:var(--d-line);background:radial-gradient(circle at 50% 50%,var(--d-surface),var(--c-ink) 58%)}[data-theme=dark] .map-canvas{background-image:radial-gradient(circle,color-mix(in srgb,var(--d-muted) 25%,transparent) 1px,transparent 1px)}[data-theme=dark] .map-links line{stroke:color-mix(in srgb,var(--c-orchid) 24%,var(--d-line))}[data-theme=dark] .map-node-avatars i{border-color:var(--d-surface-2)}
@media(max-width:760px){.map-toolbar{align-items:stretch;flex-direction:column}.map-toolbar-actions{align-items:stretch}.map-project-picker{flex:1}.map-project-picker select{width:100%;min-width:0}.map-scroll{overflow:visible}.map-canvas{min-width:0;height:auto;min-height:0;display:grid;grid-template-columns:1fr;gap:10px;padding:16px;overflow:visible;background-size:20px 20px}.map-links{display:none}.project-map-node,.task-map-node{position:relative;top:auto!important;left:auto!important;width:100%;transform:none}.project-map-node:hover,.task-map-node:hover{transform:translateY(-1px)}.project-map-node{min-height:112px;border-radius:18px}.task-map-node{min-height:82px}.map-empty{position:static;transform:none;padding:12px}.map-legend{gap:7px 12px}}
</style>
