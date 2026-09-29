<template>
  <Teleport to="body">
    <Transition name="task-drawer">
      <div class="task-drawer" role="dialog" aria-modal="true" aria-labelledby="task-drawer-title">
        <button class="task-drawer-backdrop" type="button" aria-label="Close task creation" @click="requestClose" />
        <section ref="panel" class="task-drawer-panel">
          <template v-if="createdTask">
            <div class="task-create-success">
              <span class="success-mark">✓</span>
              <p>Task created</p>
              <h2 id="task-drawer-title">{{ createdTask.subject }}</h2>
              <small>{{ createdTask.name }}</small>
              <div>
                <button class="drawer-secondary" type="button" @click="requestClose">Close</button>
                <button class="drawer-primary" type="button" @click="requestClose">View board</button>
              </div>
            </div>
          </template>

          <template v-else>
            <header class="task-drawer-header">
              <div>
                <p>Create task</p>
                <h2 id="task-drawer-title">New task</h2>
                <span>{{ projectName }}</span>
              </div>
              <button type="button" aria-label="Close" @click="requestClose">×</button>
            </header>

            <div v-if="loading" class="task-drawer-state">
              <span class="spinner" />
              <p>Loading task form…</p>
            </div>

            <div v-else-if="loadError" class="task-drawer-state task-drawer-error">
              <strong>Could not load the task form.</strong>
              <p>{{ loadError }}</p>
              <button class="drawer-secondary" type="button" @click="loadOptions">Try again</button>
            </div>

            <form v-else class="task-create-form" novalidate @submit.prevent="submitTask">
              <div class="task-form-section">
                <div class="task-form-section-heading">
                  <p>Task details</p>
                  <span>Define what needs to be done and where it starts.</span>
                </div>

                <label class="task-field task-field-wide">
                  <span>Task name <b>*</b></span>
                  <input
                    ref="subjectInput"
                    v-model.trim="form.subject"
                    type="text"
                    maxlength="140"
                    autocomplete="off"
                    placeholder="e.g. Prepare project launch checklist"
                    required
                  />
                </label>

                <div class="task-form-grid">
                  <label class="task-field">
                    <span>Priority <b>*</b></span>
                    <PomasSelect v-model="form.priority" label="Task priority" :options="options.priorities.map((priority) => ({ value: priority, label: priority }))" />
                  </label>

                  <UserPicker v-model="form.assigned_to_users" :users="options.members" label="Assign to" help="Add Project members who should work on this task. Assigned Tasks start in Working." />
                </div>
              </div>

              <div class="task-form-section">
                <div class="task-form-section-heading">
                  <p>Schedule and effort</p>
                  <span>Dates are optional and must stay inside the Project timeline.</span>
                </div>

                <div class="task-form-grid">
                  <label class="task-field">
                    <span>Start date <em>Optional</em></span>
                    <input v-model="form.exp_start_date" type="date" :max="projectDueDate || undefined" />
                  </label>

                  <label class="task-field">
                    <span>Due date <em>Optional</em></span>
                    <input v-model="form.exp_end_date" type="date" :max="projectDueDate || undefined" />
                  </label>

                  <label class="task-field">
                    <span>Estimated hours <em>Optional</em></span>
                    <input v-model="form.expected_time" type="number" min="0" step="0.25" placeholder="0" />
                  </label>

                  <div class="task-field task-milestone-field">
                    <span>Milestone <em>Optional</em></span>
                    <label class="task-check">
                      <input v-model="form.is_milestone" type="checkbox" />
                      <span><small>Mark this as a key project checkpoint.</small></span>
                    </label>
                  </div>
                </div>
              </div>

              <div class="task-form-section">
                <div class="task-form-section-heading">
                  <p>Description</p>
                  <span>Add the expected outcome, context, or acceptance notes.</span>
                </div>

                <label class="task-field task-field-wide">
                  <span>Description <em>Optional</em></span>
                  <textarea
                    v-model="form.description"
                    rows="6"
                    maxlength="10000"
                    placeholder="Describe the task and what done should look like…"
                  />
                  <small>{{ form.description.length.toLocaleString() }} / 10,000</small>
                </label>
              </div>

              <p v-if="formError" class="task-create-error" role="alert">{{ formError }}</p>

              <footer>
                <button class="drawer-secondary" type="button" :disabled="saving" @click="requestClose">Cancel</button>
                <button class="drawer-primary" type="submit" :disabled="saving">
                  {{ saving ? "Creating…" : "Create task" }}
                </button>
              </footer>
            </form>
          </template>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import UserPicker from "./UserPicker.vue"
import PomasSelect from "./PomasSelect.vue"
import {
  callPms,
  type CreateTaskResult,
  type TaskFormOptions,
} from "../services/api"

const props = defineProps<{
  project: string
  projectName: string
  projectDueDate?: string
}>()

const emit = defineEmits<{ close: []; created: [task: CreateTaskResult] }>()

const panel = ref<HTMLElement | null>(null)
const subjectInput = ref<HTMLInputElement | null>(null)
const loading = ref(true)
const saving = ref(false)
const loadError = ref("")
const formError = ref("")
const createdTask = ref<CreateTaskResult | null>(null)
const options = reactive<TaskFormOptions>({ statuses: [], priorities: [], members: [] })
const form = reactive({
  subject: "",
  priority: "Medium",
  assigned_to_users: [] as string[],
  exp_start_date: "",
  exp_end_date: "",
  expected_time: "",
  description: "",
  is_milestone: false,
})
const previousOverflow = document.body.style.overflow

onMounted(() => {
  document.body.style.overflow = "hidden"
  document.addEventListener("keydown", handleKeydown)
  loadOptions()
})

onBeforeUnmount(() => {
  document.body.style.overflow = previousOverflow
  document.removeEventListener("keydown", handleKeydown)
})

function handleKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") requestClose()
}

function requestClose() {
  if (!saving.value) emit("close")
}

async function loadOptions() {
  loading.value = true
  loadError.value = ""
  try {
    const data = await callPms<TaskFormOptions>("pms.api.get_task_form_options", { project: props.project })
    options.statuses = data.statuses
    options.priorities = data.priorities
    options.members = data.members
    form.priority = data.priorities.includes("Medium") ? "Medium" : data.priorities[0] || ""
    await nextTick()
    subjectInput.value?.focus()
  } catch (reason) {
    loadError.value = reason instanceof Error ? reason.message : "Unable to load task options."
  } finally {
    loading.value = false
  }
}

async function submitTask() {
  formError.value = ""
  if (!form.subject) {
    formError.value = "Enter a task name."
    subjectInput.value?.focus()
    return
  }
  if (form.exp_start_date && form.exp_end_date && form.exp_start_date > form.exp_end_date) {
    formError.value = "Due date must be on or after the start date."
    return
  }
  if (form.expected_time && Number(form.expected_time) < 0) {
    formError.value = "Estimated hours cannot be negative."
    return
  }

  saving.value = true
  try {
    const task = await callPms<CreateTaskResult>("pms.api.create_task", {
      project: props.project,
      subject: form.subject,
      priority: form.priority,
      assigned_to_users: form.assigned_to_users,
      exp_start_date: form.exp_start_date || null,
      exp_end_date: form.exp_end_date || null,
      expected_time: form.expected_time || 0,
      description: form.description,
      is_milestone: form.is_milestone,
    })
    createdTask.value = task
    emit("created", task)
  } catch (reason) {
    formError.value = reason instanceof Error ? reason.message : "Unable to create this task."
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.task-drawer { position: fixed; inset: 0; z-index: 500; display: flex; justify-content: flex-end; }
.task-drawer-backdrop { position: absolute; inset: 0; border: 0; background: rgba(12, 9, 20, .5); backdrop-filter: blur(2px); cursor: default; }
.task-drawer-panel { position: relative; z-index: 1; width: min(620px, 96vw); height: 100%; overflow-y: auto; padding: 28px; background: var(--bg); color: var(--text-2); box-shadow: -18px 0 48px rgba(12, 9, 20, .24); }
.task-drawer-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; padding-bottom: 20px; border-bottom: 1px solid var(--line); }
.task-drawer-header p, .task-form-section-heading p, .task-create-success > p { margin: 0; color: var(--c-violet); font-size: 10px; font-weight: 850; letter-spacing: .11em; text-transform: uppercase; }
.task-drawer-header h2 { margin: 6px 0; color: var(--c-ink); font-size: 25px; letter-spacing: -.035em; }
.task-drawer-header span, .task-form-section-heading span { color: var(--muted); font-size: 12px; }
.task-drawer-header > button { display: grid; place-items: center; flex: 0 0 36px; width: 36px; height: 36px; padding: 0; border: 1px solid var(--line); border-radius: 10px; background: white; color: var(--text-2); font-size: 23px; cursor: pointer; }
.task-create-form { margin-top: 20px; }
.task-form-section { margin-bottom: 24px; padding-bottom: 24px; border-bottom: 1px solid var(--line-soft); }
.task-form-section-heading { display: grid; gap: 5px; margin-bottom: 16px; }
.task-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 15px 14px; }
.task-field { display: grid; align-content: start; gap: 7px; min-width: 0; color: var(--text-2); font-size: 11px; font-weight: 800; }
.task-field-wide { grid-column: 1 / -1; }
.task-field > span { display: flex; align-items: center; gap: 5px; }
.task-field b { color: #d14f5a; }
.task-field em { margin-left: auto; color: var(--faint); font-size: 9px; font-style: normal; font-weight: 700; text-transform: uppercase; }
.task-field input, .task-field select, .task-field textarea { width: 100%; min-height: 43px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 9px; outline: none; background: white; color: var(--c-ink); font-size: 12px; font-weight: 500; transition: border-color .15s, box-shadow .15s; }
.task-field textarea { min-height: 120px; resize: vertical; line-height: 1.55; }
.task-field input:focus, .task-field select:focus, .task-field textarea:focus { border-color: var(--c-violet); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-violet) 16%, transparent); }
.task-field > small { color: var(--faint); font-size: 9px; font-weight: 600; }
.task-milestone-field { align-self: end; }
.task-check { min-height: 43px; display: flex; align-items: center; gap: 10px; align-self: end; padding: 11px 12px; border: 1px solid var(--line); border-radius: 9px; background: white; cursor: pointer; }
.task-check input { flex: 0 0 17px; width: 17px; min-height: 17px; height: 17px; padding: 0; accent-color: var(--c-violet); }
.task-check span { display: grid; gap: 3px; }
.task-check small { color: var(--faint); font-size: 9px; font-weight: 600; }
.task-create-form footer { position: sticky; bottom: -28px; display: flex; justify-content: flex-end; gap: 9px; margin: 0 -28px -28px; padding: 18px 28px; border-top: 1px solid var(--line); background: color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter: blur(10px); }
.drawer-primary, .drawer-secondary { min-height: 40px; padding: 0 15px; border-radius: 9px; font-size: 12px; font-weight: 800; cursor: pointer; }
.drawer-primary { border: 1px solid var(--c-violet); background: var(--c-violet); color: white; }
.drawer-secondary { border: 1px solid var(--line); background: white; color: var(--text-2); }
.drawer-primary:disabled, .drawer-secondary:disabled { cursor: wait; opacity: .6; }
.task-create-error { position: fixed; z-index: 700; top: 18px; left: 50%; width: min(460px, calc(100vw - 32px)); margin: 0; padding: 11px 12px; border: 1px solid #ffd2d6; border-radius: 9px; background: #fff0f1; color: #b83f4a; font-size: 11px; line-height: 1.5; box-shadow: 0 14px 34px rgba(12, 9, 20, .22); transform: translateX(-50%); }
.task-drawer-state, .task-create-success { min-height: 70vh; display: grid; place-content: center; justify-items: center; gap: 10px; text-align: center; }
.task-drawer-state p { max-width: 360px; margin: 0; color: var(--muted); font-size: 12px; line-height: 1.55; }
.task-drawer-error strong { color: var(--c-ink); }
.success-mark { display: grid; place-items: center; width: 52px; height: 52px; border-radius: 50%; background: var(--c-lavender); color: var(--c-violet); font-size: 25px; font-weight: 900; }
.task-create-success h2 { max-width: 410px; margin: 4px 0 0; color: var(--c-ink); font-size: 23px; }
.task-create-success > small { color: var(--muted); font-size: 11px; }
.task-create-success > div { display: flex; gap: 9px; margin-top: 14px; }
.task-drawer-enter-active, .task-drawer-leave-active { transition: opacity .18s ease; }
.task-drawer-enter-active .task-drawer-panel, .task-drawer-leave-active .task-drawer-panel { transition: transform .2s ease; }
.task-drawer-enter-from, .task-drawer-leave-to { opacity: 0; }
.task-drawer-enter-from .task-drawer-panel, .task-drawer-leave-to .task-drawer-panel { transform: translateX(28px); }
[data-theme="dark"] .task-drawer-panel { background: var(--c-ink); color: var(--c-lavender); }
[data-theme="dark"] .task-drawer-header h2, [data-theme="dark"] .task-create-success h2, [data-theme="dark"] .task-drawer-error strong { color: var(--d-title); }
[data-theme="dark"] .task-drawer-header > button, [data-theme="dark"] .task-field input, [data-theme="dark"] .task-field select, [data-theme="dark"] .task-field textarea, [data-theme="dark"] .task-check, [data-theme="dark"] .drawer-secondary { border-color: var(--d-line); background: var(--d-surface-2); color: var(--c-lavender); }
[data-theme="dark"] .task-create-form footer { border-color: var(--d-line); background: color-mix(in srgb, var(--c-ink) 92%, transparent); }
[data-theme="dark"] .task-form-section { border-color: var(--d-line); }
[data-theme="dark"] .task-create-error { border-color: #5c2631; background: #35181f; color: #ffb8c0; }
@media (max-width: 600px) {
  .task-drawer-panel { width: 100%; padding: 22px 18px; }
  .task-form-grid { grid-template-columns: 1fr; }
  .task-create-form footer { bottom: -22px; margin: 0 -18px -22px; padding: 15px 18px; }
}
</style>
