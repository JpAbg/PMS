<template>
  <Teleport to="body">
    <Transition name="task-drawer">
      <div class="task-edit-drawer" role="dialog" aria-modal="true" aria-labelledby="task-edit-title">
        <button class="task-edit-backdrop" type="button" aria-label="Close task editor" @click="requestClose" />
        <section class="task-edit-panel">
          <header>
            <div><p>Edit open task</p><h2 id="task-edit-title">{{ task.subject }}</h2><span>{{ task.project_name || task.project }}</span></div>
            <button type="button" aria-label="Close" @click="requestClose">×</button>
          </header>
          <div v-if="loading" class="task-edit-state"><span class="spinner" /><p>Loading edit form…</p></div>
          <div v-else-if="loadError" class="task-edit-state"><strong>Could not load this task editor.</strong><p>{{ loadError }}</p><button class="edit-secondary" @click="loadOptions">Try again</button></div>
          <form v-else novalidate @submit.prevent="saveTask">
            <section>
              <p>Task details</p>
              <label class="edit-field"><span>Task name <b>*</b></span><input ref="subjectInput" v-model.trim="form.subject" maxlength="140" required /></label>
              <div class="edit-grid">
                <label class="edit-field"><span>Priority <b>*</b></span><PomasSelect v-model="form.priority" label="Task priority" :options="options.priorities.map((priority) => ({ value: priority, label: priority }))" /></label>
                <UserPicker v-model="form.assigned_to_users" :users="options.members" label="Task team" />
              </div>
              <small v-if="form.assigned_to_users.length" class="assignment-note">Saving with assignees moves this task to Working.</small>
            </section>
            <section>
              <p>Schedule and effort</p>
              <div class="edit-grid">
                <label class="edit-field"><span>Start date</span><input v-model="form.exp_start_date" type="date" /></label>
                <label class="edit-field"><span>Due date</span><input v-model="form.exp_end_date" type="date" /></label>
                <label class="edit-field"><span>Estimated hours</span><input v-model="form.expected_time" type="number" min="0" step="0.25" /></label>
                <label class="edit-check"><input v-model="form.is_milestone" type="checkbox" /><span>Milestone</span></label>
              </div>
            </section>
            <section>
              <p>Description</p>
              <label class="edit-field"><span>Description</span><textarea v-model="form.description" rows="7" maxlength="10000" /><small>{{ form.description.length.toLocaleString() }} / 10,000</small></label>
            </section>
            <p v-if="formError" class="edit-error" role="alert">{{ formError }}</p>
            <footer><button class="edit-secondary" type="button" :disabled="saving" @click="requestClose">Cancel</button><button class="edit-primary" type="submit" :disabled="saving">{{ saving ? "Saving…" : "Save changes" }}</button></footer>
          </form>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import UserPicker from "./UserPicker.vue"
import PomasSelect from "./PomasSelect.vue"
import { callPms, type TaskDetails, type TaskFormOptions } from "../services/api"

const props = defineProps<{ task: TaskDetails }>()
const emit = defineEmits<{ close: []; updated: [task: TaskDetails] }>()
const subjectInput = ref<HTMLInputElement | null>(null)
const loading = ref(true)
const saving = ref(false)
const loadError = ref("")
const formError = ref("")
const options = reactive<TaskFormOptions>({ statuses: [], priorities: [], members: [] })
const form = reactive({ subject: props.task.subject, priority: props.task.priority, assigned_to_users: [] as string[], exp_start_date: props.task.exp_start_date || "", exp_end_date: props.task.exp_end_date || "", expected_time: props.task.expected_time ? String(props.task.expected_time) : "", description: props.task.description || "", is_milestone: Boolean(props.task.is_milestone) })
const previousOverflow = document.body.style.overflow

onMounted(() => { document.body.style.overflow = "hidden"; document.addEventListener("keydown", onKey); loadOptions() })
onBeforeUnmount(() => { document.body.style.overflow = previousOverflow; document.removeEventListener("keydown", onKey) })
function onKey(event: KeyboardEvent) { if (event.key === "Escape") requestClose() }
function requestClose() { if (!saving.value) emit("close") }
async function loadOptions() {
  if (!props.task.project) { loadError.value = "The task project is unavailable."; loading.value = false; return }
  loading.value = true; loadError.value = ""
  try { const data = await callPms<TaskFormOptions>("pms.api.get_task_form_options", { project: props.task.project }); options.statuses = data.statuses; options.priorities = data.priorities; options.members = data.members; await nextTick(); subjectInput.value?.focus() } catch (reason) { loadError.value = reason instanceof Error ? reason.message : "Unable to load task options." } finally { loading.value = false }
}
async function saveTask() {
  formError.value = ""
  if (!form.subject) { formError.value = "Enter a task name."; subjectInput.value?.focus(); return }
  if (form.exp_start_date && form.exp_end_date && form.exp_start_date > form.exp_end_date) { formError.value = "Due date must be on or after the start date."; return }
  saving.value = true
  try { const updated = await callPms<TaskDetails>("pms.api.update_open_task", { task: props.task.name, ...form }); emit("updated", updated) } catch (reason) { formError.value = reason instanceof Error ? reason.message : "Unable to save this task." } finally { saving.value = false }
}
</script>

<style scoped>
.task-edit-drawer{position:fixed;inset:0;z-index:510;display:flex;justify-content:flex-end}.task-edit-backdrop{position:absolute;inset:0;border:0;background:rgba(12,9,20,.5);backdrop-filter:blur(2px)}.task-edit-panel{position:relative;z-index:1;width:min(640px,96vw);height:100%;overflow-y:auto;padding:28px;background:var(--bg);color:var(--text-2);box-shadow:-18px 0 48px rgba(12,9,20,.24)}.task-edit-panel header{display:flex;justify-content:space-between;gap:18px;padding-bottom:20px;border-bottom:1px solid var(--line)}.task-edit-panel header p,.task-edit-panel form>section>p{margin:0;color:var(--c-violet);font-size:10px;font-weight:850;letter-spacing:.11em;text-transform:uppercase}.task-edit-panel h2{margin:6px 0;color:var(--c-ink);font-size:25px;letter-spacing:-.035em}.task-edit-panel header span{color:var(--muted);font-size:12px}.task-edit-panel header>button{width:36px;height:36px;border:1px solid var(--line);border-radius:10px;background:white;color:var(--text-2);font-size:23px;cursor:pointer}.task-edit-panel form{margin-top:20px}.task-edit-panel form>section{margin-bottom:24px;padding-bottom:24px;border-bottom:1px solid var(--line-soft)}.task-edit-panel form>section>p{margin-bottom:16px}.edit-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.edit-field{display:grid;gap:7px;margin-bottom:14px;color:var(--text-2);font-size:11px;font-weight:800}.edit-field>span{display:flex;gap:5px}.edit-field b{color:#d14f5a}.edit-field em{color:var(--faint);font-size:9px;font-style:normal;margin-left:auto}.edit-field input,.edit-field select,.edit-field textarea{width:100%;min-height:43px;padding:10px 12px;border:1px solid var(--line);border-radius:9px;background:white;color:var(--c-ink);font-size:12px;outline:none}.edit-field textarea{resize:vertical;line-height:1.55}.edit-field input:focus,.edit-field select:focus,.edit-field textarea:focus{border-color:var(--c-violet);box-shadow:0 0 0 3px color-mix(in srgb,var(--c-violet) 16%,transparent)}.edit-field small{color:var(--faint);font-size:9px;text-align:right}.edit-check{display:flex;align-items:center;gap:9px;align-self:end;min-height:43px;padding:10px 12px;border:1px solid var(--line);border-radius:9px;background:white;font-size:11px;font-weight:800}.edit-check input{width:17px;height:17px;accent-color:var(--c-violet)}.assignment-note{display:block;margin-top:-5px;color:var(--c-violet);font-size:10px;font-weight:700}.edit-error{position:fixed;z-index:700;top:18px;left:50%;width:min(460px,calc(100vw - 32px));margin:0;padding:11px 12px;border:1px solid #ffd2d6;border-radius:9px;background:#fff0f1;color:#b83f4a;font-size:11px;transform:translateX(-50%);box-shadow:0 14px 34px rgba(12,9,20,.22)}.task-edit-panel footer{position:sticky;bottom:-28px;display:flex;justify-content:flex-end;gap:9px;margin:0 -28px -28px;padding:18px 28px;border-top:1px solid var(--line);background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(10px)}.edit-primary,.edit-secondary{min-height:40px;padding:0 15px;border-radius:9px;font-size:12px;font-weight:800;cursor:pointer}.edit-primary{border:1px solid var(--c-violet);background:var(--c-violet);color:white}.edit-secondary{border:1px solid var(--line);background:white;color:var(--text-2)}.task-edit-state{min-height:70vh;display:grid;place-content:center;justify-items:center;gap:10px;text-align:center;color:var(--muted);font-size:12px}.task-edit-state strong{color:var(--c-ink)}[data-theme=dark] .task-edit-panel{background:var(--c-ink);color:var(--c-lavender)}[data-theme=dark] .task-edit-panel h2,[data-theme=dark] .task-edit-state strong{color:var(--d-title)}[data-theme=dark] .task-edit-panel header>button,[data-theme=dark] .edit-field input,[data-theme=dark] .edit-field select,[data-theme=dark] .edit-field textarea,[data-theme=dark] .edit-check,[data-theme=dark] .edit-secondary{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .task-edit-panel form>section,[data-theme=dark] .task-edit-panel footer{border-color:var(--d-line)}[data-theme=dark] .task-edit-panel footer{background:color-mix(in srgb,var(--c-ink) 92%,transparent)}@media(max-width:600px){.task-edit-panel{width:100%;padding:22px 18px}.edit-grid{grid-template-columns:1fr}.task-edit-panel footer{bottom:-22px;margin:0 -18px -22px;padding:15px 18px}}
</style>
