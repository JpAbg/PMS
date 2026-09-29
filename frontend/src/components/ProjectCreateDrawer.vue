<template>
  <Teleport to="body">
    <Transition name="side-drawer">
      <div class="side-drawer" role="dialog" aria-modal="true" aria-labelledby="project-drawer-title">
        <button class="drawer-backdrop" type="button" aria-label="Close project creation" @click="requestClose" />
        <section class="drawer-panel">
          <template v-if="createdProject">
            <div class="drawer-state success-state">
              <span class="success-mark">✓</span>
              <p>Project created</p>
              <h2 id="project-drawer-title">{{ createdProject.project_name }}</h2>
              <button class="drawer-primary" type="button" @click="openCreated">Open project</button>
            </div>
          </template>
          <template v-else>
            <header class="drawer-header">
              <div><p>Create project</p><h2 id="project-drawer-title">New project</h2><span>Start a new Pomas workspace backed by ERPNext.</span></div>
              <button type="button" aria-label="Close" @click="requestClose">×</button>
            </header>
            <form class="drawer-form" novalidate @submit.prevent="submitProject">
              <label class="drawer-field">
                <span>Project name <b>*</b></span>
                <input ref="nameInput" v-model.trim="form.project_name" maxlength="140" placeholder="e.g. Customer portal rollout" required />
              </label>
              <section class="drawer-field field-wide client-project-field">
                <span>Client <em>Optional</em></span>
                <div class="client-picker-row"><PomasSelect v-model="form.customer" label="Project client" :options="clientOptions" /><button class="client-create-trigger" type="button" @click="clientDrawerOpen = true">+ New client</button></div>
              </section>
              <div class="field-grid">
                <label class="drawer-field"><span>Start date <em>Optional</em></span><input v-model="form.expected_start_date" type="date" /></label>
                <label class="drawer-field"><span>Due date <em>Optional</em></span><input v-model="form.expected_end_date" type="date" /></label>
                <label class="drawer-field field-wide"><span>Priority <b>*</b></span><PomasSelect v-model="form.priority" label="Project priority" :options="priorityOptions" /></label>
              </div>
              <section class="drawer-field field-wide github-create-section">
                <span>GitHub repository <em>Optional</em></span>
                <div class="github-choice">
                  <button type="button" :class="{ active: githubMode === 'create' }" @click="githubMode = 'create'"><b>Create new repository</b><small>Private repository in the connected organization</small></button>
                  <button type="button" :class="{ active: githubMode === 'existing' }" @click="githubMode = 'existing'"><b>Link existing repository</b><small>Use a repository your team already has</small></button>
                </div>
                <label v-if="githubMode === 'create'" class="github-create-input"><span>New repository name</span><input v-model.trim="repositoryName" maxlength="100" placeholder="project-name" /></label>
                <label v-else-if="githubMode === 'existing'" class="github-create-input"><span>Repository URL</span><input v-model.trim="form.github_repository_url" type="url" maxlength="300" placeholder="https://github.com/owner/repository" /></label>
                <small class="field-help">Current organization connection: <b>{{ githubConnectionLoading ? 'Loading…' : (githubConnection || 'Not connected') }}</b></small>
              </section>
              <label class="drawer-field"><span>Description <em>Optional</em></span><textarea v-model="form.description" maxlength="10000" rows="7" placeholder="Goals, scope, and expected outcome…" /></label>
              <label class="drawer-field"><span>Project logo <em>Optional PNG</em></span><input ref="logoInput" class="logo-file-input" type="file" hidden accept="image/png" @change="selectLogo" /><div class="logo-file-control"><button type="button" @click="chooseLogo">Choose PNG</button><small>{{ logoFile ? logoFile.name : "No file selected" }}</small></div></label>
              <UserPicker v-model="form.members" :users="memberOptions" label="Project members" help="Add the Pomas people who may see and work on this Project. You are included automatically." />
              <p v-if="formError" class="viewport-alert" role="alert">{{ formError }}</p>
              <footer><button class="drawer-secondary" type="button" :disabled="saving" @click="requestClose">Cancel</button><button class="drawer-primary" type="submit" :disabled="saving">{{ saving ? "Creating…" : "Create project" }}</button></footer>
            </form>
          </template>
        </section>
      </div>
    </Transition>
  </Teleport>
  <ClientCreateDrawer v-if="clientDrawerOpen" @close="clientDrawerOpen = false" @created="handleClientCreated" />
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import UserPicker from "./UserPicker.vue"
import PomasSelect from "./PomasSelect.vue"
import ClientCreateDrawer from "./ClientCreateDrawer.vue"
import { callPms, uploadPms, type CreateProjectResult, type TaskFormMember } from "../services/api"
const githubMode = ref<"create" | "existing" | null>(null)
const repositoryName = ref("")
const githubConnection = ref("")
const githubConnectionLoading = ref(false)
const clientDrawerOpen = ref(false)

const emit = defineEmits<{ close: []; created: [project: CreateProjectResult]; open: [project: CreateProjectResult] }>()
const nameInput = ref<HTMLInputElement | null>(null)
const logoInput = ref<HTMLInputElement | null>(null)
const saving = ref(false)
const formError = ref("")
const form = reactive({ project_name: "", expected_start_date: "", expected_end_date: "", priority: "Medium", description: "", customer: "", github_repository_url: "", members: [] as string[] })
const memberOptions = ref<TaskFormMember[]>([])
const clients = ref<{ name: string; customer_name: string }[]>([])
const clientOptions = computed(() => [{ value: "", label: "No client selected" }, ...clients.value.map((client) => ({ value: client.name, label: client.customer_name || client.name }))])
const createdProject = ref<CreateProjectResult | null>(null)
const priorityOptions = ["Low", "Medium", "High", "Urgent"].map((value) => ({ value, label: value }))
const logoFile = ref<File | null>(null)
const previousOverflow = document.body.style.overflow
onMounted(async () => { document.body.style.overflow = "hidden"; document.addEventListener("keydown", onKey); githubConnectionLoading.value = true; try { const [members, connection, clientList] = await Promise.all([callPms<TaskFormMember[]>("pms.api.get_project_member_options"), callPms<{ enabled: boolean; organization: string }>("pms.api.get_github_connection_summary"), callPms<{ name: string; customer_name: string }[]>("pms.api.get_clients")]); memberOptions.value = members; githubConnection.value = connection.enabled ? connection.organization : ""; clients.value = clientList } catch (reason) { formError.value = reason instanceof Error ? reason.message : "Unable to load Pomas members." } finally { githubConnectionLoading.value = false } await nextTick(); nameInput.value?.focus() })
onBeforeUnmount(() => { document.body.style.overflow = previousOverflow; document.removeEventListener("keydown", onKey) })
function onKey(event: KeyboardEvent) { if (event.key === "Escape") requestClose() }
function chooseLogo() { logoInput.value?.click() }
function selectLogo(event: Event) { logoFile.value = (event.target as HTMLInputElement).files?.[0] || null }
function handleClientCreated(client: { name: string; customer_name: string }) { if (!clients.value.some((item) => item.name === client.name)) clients.value.push(client); clients.value.sort((left, right) => (left.customer_name || left.name).localeCompare(right.customer_name || right.name)); form.customer = client.name; clientDrawerOpen.value = false }
function requestClose() { if (!saving.value) emit("close") }
function openCreated() { if (createdProject.value) emit("open", createdProject.value) }
async function submitProject() {
  formError.value = ""
  if (!form.project_name) { formError.value = "Enter a project name."; nameInput.value?.focus(); return }
  if (form.expected_start_date && form.expected_end_date && form.expected_start_date > form.expected_end_date) { formError.value = "Due date must be on or after the start date."; return }
  if (githubMode.value === "existing" && !form.github_repository_url) { formError.value = "Enter the repository URL to link it."; return }
  if (githubMode.value === "create" && !repositoryName.value) { formError.value = "Enter a name for the new repository."; return }
  if (githubMode.value === "create" && !githubConnection.value) { formError.value = "Connect a GitHub organization in Settings before creating a repository."; return }
  saving.value = true
  try {
    const project = await callPms<CreateProjectResult>("pms.api.create_project", { ...form, github_repository_url: githubMode.value === "existing" ? form.github_repository_url : "", expected_start_date: form.expected_start_date || null, expected_end_date: form.expected_end_date || null })
    if (githubMode.value === "create") await callPms("pms.api.create_project_github_repository", { project: project.name, repository_name: repositoryName.value })
    createdProject.value = project
    if (logoFile.value) { const data = new FormData(); data.append("project", project.name); data.append("logo", logoFile.value, logoFile.value.name); await uploadPms("pms.api.upload_project_logo", data) }
    emit("created", project)
  } catch (reason) { formError.value = reason instanceof Error ? reason.message : "Unable to create this project." }
  finally { saving.value = false }
}
</script>

<style scoped>
.side-drawer{position:fixed;inset:0;z-index:500;display:flex;justify-content:flex-end}.drawer-backdrop{position:absolute;inset:0;border:0;background:rgba(12,9,20,.5);backdrop-filter:blur(2px)}.drawer-panel{position:relative;z-index:1;width:min(580px,96vw);height:100%;overflow-y:auto;padding:28px;background:var(--bg);color:var(--text-2);box-shadow:-18px 0 48px rgba(12,9,20,.24)}.drawer-header{display:flex;justify-content:space-between;gap:18px;padding-bottom:20px;border-bottom:1px solid var(--line)}.drawer-header p,.success-state>p{margin:0;color:var(--c-violet);font-size:10px;font-weight:850;letter-spacing:.11em;text-transform:uppercase}.drawer-header h2,.success-state h2{margin:6px 0;color:var(--c-ink);font-size:25px;letter-spacing:-.035em}.drawer-header span{color:var(--muted);font-size:12px}.drawer-header>button{width:36px;height:36px;border:1px solid var(--line);border-radius:10px;background:white;color:var(--text-2);font-size:23px;cursor:pointer}.drawer-form{display:grid;gap:20px;margin-top:24px}.field-grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}.field-wide{grid-column:1/-1}.drawer-field{display:grid;gap:7px;color:var(--text-2);font-size:11px;font-weight:800}.drawer-field>span{display:flex}.drawer-field b{color:#d14f5a}.drawer-field em{margin-left:auto;color:var(--faint);font-size:9px;font-style:normal;text-transform:uppercase}.drawer-field input,.drawer-field select,.drawer-field textarea{width:100%;min-height:43px;padding:10px 12px;border:1px solid var(--line);border-radius:9px;outline:none;background:white;color:var(--c-ink)}.drawer-field textarea{resize:vertical;line-height:1.55}.drawer-field input:focus,.drawer-field select:focus,.drawer-field textarea:focus{border-color:var(--c-violet);box-shadow:0 0 0 3px color-mix(in srgb,var(--c-violet) 16%,transparent)}footer{position:sticky;bottom:-28px;display:flex;justify-content:flex-end;gap:9px;margin:4px -28px -28px;padding:18px 28px;border-top:1px solid var(--line);background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(10px)}.drawer-primary,.drawer-secondary{min-height:40px;padding:0 15px;border-radius:9px;font-size:12px;font-weight:800;cursor:pointer}.drawer-primary{border:1px solid var(--c-violet);background:var(--c-violet);color:white}.drawer-secondary{border:1px solid var(--line);background:white;color:var(--text-2)}.drawer-state{min-height:70vh;display:grid;place-content:center;justify-items:center;gap:12px;text-align:center}.success-mark{display:grid;place-items:center;width:52px;height:52px;border-radius:50%;background:var(--c-lavender);color:var(--c-violet);font-size:25px;font-weight:900}.viewport-alert{position:fixed;z-index:700;top:18px;left:50%;width:min(460px,calc(100vw - 32px));margin:0;padding:11px 12px;border:1px solid #ffd2d6;border-radius:9px;background:#fff0f1;color:#b83f4a;font-size:11px;box-shadow:0 14px 34px rgba(12,9,20,.22);transform:translateX(-50%)}.side-drawer-enter-active,.side-drawer-leave-active{transition:opacity .18s}.side-drawer-enter-active .drawer-panel,.side-drawer-leave-active .drawer-panel{transition:transform .2s}.side-drawer-enter-from,.side-drawer-leave-to{opacity:0}.side-drawer-enter-from .drawer-panel,.side-drawer-leave-to .drawer-panel{transform:translateX(28px)}[data-theme=dark] .drawer-panel{background:var(--c-ink);color:var(--c-lavender)}[data-theme=dark] .drawer-header h2,[data-theme=dark] .success-state h2{color:var(--d-title)}[data-theme=dark] .drawer-header>button,[data-theme=dark] .drawer-field input,[data-theme=dark] .drawer-field select,[data-theme=dark] .drawer-field textarea,[data-theme=dark] .drawer-secondary{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] footer{border-color:var(--d-line);background:color-mix(in srgb,var(--c-ink) 92%,transparent)}[data-theme=dark] .viewport-alert{border-color:#5c2631;background:#35181f;color:#ffb8c0}@media(max-width:600px){.drawer-panel{width:100%;padding:22px 18px}.field-grid{grid-template-columns:1fr}footer{bottom:-22px;margin:4px -18px -22px;padding:15px 18px}}
.logo-file-input{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}.logo-file-control{display:flex;align-items:center;gap:11px;min-height:43px;padding:5px;border:1px dashed var(--line);border-radius:10px;background:color-mix(in srgb,var(--c-lavender) 18%,white)}.logo-file-control button{min-height:31px;padding:0 11px;border:1px solid var(--c-violet);border-radius:7px;background:white;color:var(--c-violet);font-size:10px;font-weight:850;cursor:pointer}.logo-file-control button:hover{background:var(--c-lavender)}.logo-file-control small{min-width:0;overflow:hidden;color:var(--muted);font-size:10px;font-weight:650;text-overflow:ellipsis;white-space:nowrap}[data-theme=dark] .logo-file-control{border-color:var(--d-line);background:var(--d-hover)}[data-theme=dark] .logo-file-control button{border-color:var(--c-orchid);background:var(--d-surface-2);color:var(--c-orchid)}[data-theme=dark] .logo-file-control small{color:var(--d-muted)}
.client-project-field{gap:7px}.client-picker-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:9px}.client-create-trigger{min-height:43px;padding:0 12px;border:1px solid var(--line);border-radius:9px;background:white;color:var(--text-2);font-size:10px;font-weight:850;cursor:pointer}.client-create-trigger:hover{background:var(--line-soft)}[data-theme=dark] .client-create-trigger{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}@media(max-width:600px){.client-picker-row{grid-template-columns:1fr}.client-create-trigger{width:100%}}
.github-create-section{padding:15px;border:1px solid var(--line);border-radius:12px;background:var(--line-soft)}.github-choice{display:grid;grid-template-columns:1fr 1fr;gap:9px}.github-choice button{display:grid;gap:4px;min-height:64px;padding:11px;border:1px solid var(--line);border-radius:10px;background:white;color:var(--text-2);text-align:left;cursor:pointer}.github-choice button:hover,.github-choice button.active{border-color:var(--c-violet);background:var(--c-lavender);color:var(--c-violet)}.github-choice b{font-size:11px}.github-choice small,.github-create-input span{color:var(--muted);font-size:10px;font-weight:650}.github-create-input{display:grid;gap:6px;margin-top:11px}.field-help{margin-top:3px;color:var(--muted);font-size:10px;font-weight:650}.field-help b{color:var(--c-violet)}[data-theme=dark] .github-create-section{border-color:var(--d-line);background:var(--d-hover)}[data-theme=dark] .github-choice button{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .github-choice button.active,[data-theme=dark] .github-choice button:hover{border-color:var(--c-orchid);background:#2a1f3c;color:var(--c-orchid)}@media(max-width:600px){.github-choice{grid-template-columns:1fr}}
/* Keep validation feedback inside the Project creation drawer. */.drawer-panel .viewport-alert{position:absolute;top:104px;left:20px;right:20px;width:auto;margin:0;transform:none}
</style>
