<template>
  <Teleport to="body">
    <Transition name="work-drawer">
      <div class="work-drawer" role="dialog" aria-modal="true" aria-labelledby="work-drawer-title">
        <button class="work-backdrop" type="button" aria-label="Close work submission" @click="requestClose" />
        <section class="work-panel">
          <template v-if="submitted">
            <div class="work-success">
              <span>✓</span>
              <p>Work submitted</p>
              <h2 id="work-drawer-title">{{ task.subject }}</h2>
              <small>{{ submitted.name }} · {{ submitted.file_count }} {{ submitted.file_count === 1 ? "file" : "files" }} uploaded</small>
              <button class="work-primary" type="button" @click="requestClose">Done</button>
            </div>
          </template>

          <template v-else>
            <header class="work-header">
              <div>
                <p>Task submission</p>
                <h2 id="work-drawer-title">Submit your work</h2>
                <span>{{ task.subject }} · {{ task.name }}</span>
              </div>
              <button type="button" aria-label="Close" @click="requestClose">×</button>
            </header>

            <form class="work-form" novalidate @submit.prevent="submitWork">
              <section>
                <div class="work-section-heading">
                  <p>Summary</p>
                  <span>Describe what you completed and anything the reviewer should know.</span>
                </div>
                <label class="work-field">
                  <span>Description <b>*</b></span>
                  <textarea
                    ref="descriptionInput"
                    v-model="description"
                    rows="8"
                    maxlength="10000"
                    placeholder="Explain the work completed, decisions made, and any remaining notes…"
                    required
                  />
                  <small>{{ description.length.toLocaleString() }} / 10,000</small>
                </label>
              </section>

              <section>
                <div class="work-section-heading files-heading">
                  <div>
                    <p>Files</p>
                    <span>Select files from your computer, then choose where each should eventually live in the repository.</span>
                  </div>
                  <input
                    ref="fileInput"
                    class="native-file-input"
                    type="file"
                    multiple
                    :disabled="files.length >= 25"
                    @change="handleFileSelection"
                  />
                  <button class="add-file-button" type="button" :disabled="files.length >= 25" @click="openFilePicker">Select files</button>
                </div>

                <div v-if="!files.length" class="files-empty">
                  No files selected. You can submit a description by itself.
                </div>

                <div v-for="(file, index) in files" :key="file.id" class="file-entry">
                  <div class="file-entry-header">
                    <div class="file-entry-title"><strong>{{ file.file_name }}</strong><small>{{ formatFileSize(file.source.size) }}</small></div>
                    <button type="button" :aria-label="'Remove file ' + (index + 1)" @click="removeFile(index)">Remove</button>
                  </div>
                  <label class="work-field">
                    <span>Repository destination <b>*</b></span>
                    <input v-model.trim="file.repository_path" type="text" maxlength="1000" placeholder="e.g. apps/pms/frontend/src/components/TaskDetailDrawer.vue" />
                  </label>
                </div>
              </section>

              <p v-if="formError" class="work-error" role="alert">{{ formError }}</p>

              <footer>
                <button class="work-secondary" type="button" :disabled="saving" @click="requestClose">Cancel</button>
                <button class="work-primary" type="submit" :disabled="saving">{{ saving ? "Uploading and submitting…" : "Submit work" }}</button>
              </footer>
            </form>
          </template>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue"
import {
  uploadPms,
  type TaskDetails,
  type WorkSubmissionFile,
  type WorkSubmissionResult,
} from "../services/api"

type DraftFile = WorkSubmissionFile & { id: number; source: File }

const props = defineProps<{ task: TaskDetails }>()
const emit = defineEmits<{ close: []; submitted: [task: TaskDetails] }>()
const descriptionInput = ref<HTMLTextAreaElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const description = ref("")
const files = ref<DraftFile[]>([])
const saving = ref(false)
const formError = ref("")
const submitted = ref<WorkSubmissionResult | null>(null)
const desktopQuery = window.matchMedia("(min-width: 901px)")
const previousOverflow = document.body.style.overflow
let nextFileId = 1

onMounted(async () => {
  if (!desktopQuery.matches) {
    emit("close")
    return
  }
  document.body.style.overflow = "hidden"
  document.addEventListener("keydown", onKey)
  desktopQuery.addEventListener("change", onViewportChange)
  await nextTick()
  descriptionInput.value?.focus()
})

onBeforeUnmount(() => {
  document.body.style.overflow = previousOverflow
  document.removeEventListener("keydown", onKey)
  desktopQuery.removeEventListener("change", onViewportChange)
})

function onKey(event: KeyboardEvent) {
  if (event.key === "Escape") requestClose()
}

function onViewportChange(event: MediaQueryListEvent) {
  if (!event.matches) requestClose()
}

function requestClose() {
  if (!saving.value) emit("close")
}

function openFilePicker() {
  fileInput.value?.click()
}

function handleFileSelection(event: Event) {
  const input = event.target as HTMLInputElement
  const selected = Array.from(input.files || [])
  const available = 25 - files.value.length
  if (selected.length > available) {
    formError.value = `You can upload at most 25 files. Only the first ${available} were added.`
  }
  for (const source of selected.slice(0, available)) {
    files.value.push({
      id: nextFileId++,
      source,
      file_name: source.name,
      repository_path: source.name,
    })
  }
  input.value = ""
}

function removeFile(index: number) {
  files.value.splice(index, 1)
}

async function submitWork() {
  formError.value = ""
  if (!description.value.trim()) {
    formError.value = "Describe the work you completed."
    descriptionInput.value?.focus()
    return
  }
  if (files.value.some((file) => !file.repository_path.trim())) {
    formError.value = "Enter a repository destination for every selected file."
    return
  }

  saving.value = true
  try {
    const formData = new FormData()
    formData.append("task", props.task.name)
    formData.append("description", description.value.trim())
    formData.append("file_metadata", JSON.stringify(files.value.map(({ repository_path }) => ({ repository_path }))))
    for (const file of files.value) {
      formData.append("files", file.source, file.source.name)
    }
    submitted.value = await uploadPms<WorkSubmissionResult>("pms.api.submit_task_work", formData)
    emit("submitted", props.task)
  } catch (reason) {
    formError.value = reason instanceof Error ? reason.message : "Unable to submit your work."
  } finally {
    saving.value = false
  }
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<style scoped>
.work-drawer { position: fixed; inset: 0; z-index: 520; display: flex; justify-content: flex-end; }
.work-backdrop { position: absolute; inset: 0; border: 0; background: rgba(12, 9, 20, .5); backdrop-filter: blur(2px); }
.work-panel { position: relative; z-index: 1; width: min(640px, 96vw); height: 100%; overflow-y: auto; padding: 28px; background: var(--bg); color: var(--text-2); box-shadow: -18px 0 48px rgba(12, 9, 20, .24); }
.work-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; padding-bottom: 20px; border-bottom: 1px solid var(--line); }
.work-header p, .work-section-heading p, .work-success p { margin: 0; color: var(--c-violet); font-size: 10px; font-weight: 850; letter-spacing: .11em; text-transform: uppercase; }
.work-header h2, .work-success h2 { margin: 6px 0; color: var(--c-ink); font-size: 25px; letter-spacing: -.035em; }
.work-header span, .work-section-heading span { color: var(--muted); font-size: 12px; line-height: 1.55; }
.work-header > button { display: grid; place-items: center; flex: 0 0 36px; width: 36px; height: 36px; padding: 0; border: 1px solid var(--line); border-radius: 10px; background: white; color: var(--text-2); font-size: 23px; cursor: pointer; }
.work-form { margin-top: 20px; }
.work-form > section { margin-bottom: 24px; padding-bottom: 24px; border-bottom: 1px solid var(--line-soft); }
.work-section-heading { display: grid; gap: 5px; margin-bottom: 16px; }
.files-heading { grid-template-columns: 1fr auto; align-items: start; gap: 18px; }
.files-heading > div { display: grid; gap: 5px; }
.work-field { display: grid; gap: 7px; margin-bottom: 14px; color: var(--text-2); font-size: 11px; font-weight: 800; }
.work-field > span { display: flex; gap: 5px; }
.work-field b { color: #d14f5a; }
.work-field input, .work-field textarea { width: 100%; min-height: 43px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 9px; outline: none; background: white; color: var(--c-ink); font-size: 12px; font-weight: 500; transition: border-color .15s, box-shadow .15s; }
.work-field textarea { min-height: 150px; resize: vertical; line-height: 1.55; }
.work-field input:focus, .work-field textarea:focus { border-color: var(--c-violet); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-violet) 16%, transparent); }
.work-field small { color: var(--faint); font-size: 9px; font-weight: 600; text-align: right; }
.add-file-button { min-height: 36px; padding: 0 12px; border: 1px solid var(--c-violet); border-radius: 9px; background: transparent; color: var(--c-violet); font-size: 11px; font-weight: 800; cursor: pointer; }
.add-file-button:disabled { cursor: not-allowed; opacity: .45; }
.native-file-input { display: none; }
.files-empty { padding: 16px; border: 1px dashed var(--line); border-radius: 10px; color: var(--muted); font-size: 12px; text-align: center; }
.file-entry { margin-top: 12px; padding: 16px; border: 1px solid var(--line); border-radius: 12px; background: var(--line-soft); }
.file-entry-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 13px; }
.file-entry-header strong { color: var(--text-2); font-size: 11px; }
.file-entry-header button { padding: 0; border: 0; background: transparent; color: #b83f4a; font-size: 10px; font-weight: 800; cursor: pointer; }
.work-error { position: fixed; z-index: 700; top: 18px; left: 50%; width: min(460px, calc(100vw - 32px)); margin: 0; padding: 11px 12px; border: 1px solid #ffd2d6; border-radius: 9px; background: #fff0f1; color: #b83f4a; font-size: 11px; box-shadow: 0 14px 34px rgba(12, 9, 20, .22); transform: translateX(-50%); }
.work-form footer { position: sticky; bottom: -28px; display: flex; justify-content: flex-end; gap: 9px; margin: 0 -28px -28px; padding: 18px 28px; border-top: 1px solid var(--line); background: color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter: blur(10px); }
.file-entry-title { display: grid; gap: 3px; min-width: 0; }
.file-entry-title strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-entry-title small { color: var(--faint); font-size: 9px; font-weight: 600; }
.work-primary, .work-secondary { min-height: 40px; padding: 0 15px; border-radius: 9px; font-size: 12px; font-weight: 800; cursor: pointer; }
.work-primary { border: 1px solid var(--c-violet); background: var(--c-violet); color: white; }
.work-secondary { border: 1px solid var(--line); background: white; color: var(--text-2); }
.work-primary:disabled, .work-secondary:disabled { cursor: wait; opacity: .6; }
.work-success { min-height: 70vh; display: grid; place-content: center; justify-items: center; gap: 10px; text-align: center; }
.work-success > span { display: grid; place-items: center; width: 52px; height: 52px; border-radius: 50%; background: var(--c-lavender); color: var(--c-violet); font-size: 25px; font-weight: 900; }
.work-success small { color: var(--muted); font-size: 11px; }
.work-success button { margin-top: 14px; }
.work-drawer-enter-active, .work-drawer-leave-active { transition: opacity .18s ease; }
.work-drawer-enter-active .work-panel, .work-drawer-leave-active .work-panel { transition: transform .2s ease; }
.work-drawer-enter-from, .work-drawer-leave-to { opacity: 0; }
.work-drawer-enter-from .work-panel, .work-drawer-leave-to .work-panel { transform: translateX(28px); }
[data-theme="dark"] .work-panel { background: var(--c-ink); color: var(--c-lavender); }
[data-theme="dark"] .work-header h2, [data-theme="dark"] .work-success h2 { color: var(--d-title); }
[data-theme="dark"] .work-header > button, [data-theme="dark"] .work-field input, [data-theme="dark"] .work-field textarea, [data-theme="dark"] .work-secondary { border-color: var(--d-line); background: var(--d-surface-2); color: var(--c-lavender); }
[data-theme="dark"] .work-form > section, [data-theme="dark"] .file-entry, [data-theme="dark"] .files-empty, [data-theme="dark"] .work-form footer { border-color: var(--d-line); }
[data-theme="dark"] .file-entry { background: var(--d-surface-2); }
[data-theme="dark"] .work-form footer { background: color-mix(in srgb, var(--c-ink) 92%, transparent); }
[data-theme="dark"] .work-error { border-color: #5c2631; background: #35181f; color: #ffb8c0; }
@media (max-width: 900px) { .work-drawer { display: none; } }
</style>
