<template>
  <div ref="root" class="project-actions" @click.stop>
    <input ref="logoInput" class="project-logo-native" type="file" accept="image/png" @change="uploadLogo" />
    <button class="project-actions-trigger" type="button" aria-label="Project options" :aria-expanded="menuOpen" @click="menuOpen = !menuOpen">•••</button>
    <Transition name="project-actions-pop">
      <div v-if="menuOpen" class="project-actions-popover" role="menu">
        <button v-if="project.status !== 'Completed'" type="button" role="menuitem" @click="complete">Mark as done</button>
        <button type="button" role="menuitem" @click="openEditProject">Edit project</button>
        <p v-if="actionError" class="project-actions-error">{{ actionError }}</p>
        <button class="project-actions-danger" type="button" role="menuitem" @click="openDelete">Delete project…</button>
      </div>
    </Transition>

    <Teleport to="body">
      <Transition name="side-drawer">
        <div v-if="teamOpen" class="project-team-drawer" role="dialog" aria-modal="true" aria-labelledby="project-team-title">
          <button class="project-team-backdrop" type="button" aria-label="Close project editor" @click="closeTeam" />
          <section class="project-team-panel">
            <header class="project-team-header"><div><p>Edit project</p><h2 id="project-team-title">{{ project.project_name }}</h2><span>Update this Project’s identity and the people who can access it.</span></div><button type="button" aria-label="Close" @click="closeTeam">×</button></header>
            <div class="project-team-content">
              <section class="project-logo-section">
                <p>Project logo</p>
                <div class="project-logo-control">
                  <button class="project-logo-drop" type="button" aria-label="Choose project logo" @click="openLogoPicker"><img v-if="project.logo" :src="project.logo" alt="" /><span v-else>+</span></button>
                  <div><strong>{{ project.logo ? "Logo set" : "No logo yet" }}</strong><button class="project-logo-change" type="button" @click="openLogoPicker">{{ project.logo ? "Change logo" : "Add logo" }}</button></div>
                </div>
                <small>PNG only. It is centred and cropped to 192 × 192 pixels.</small>
              </section>
              <section class="project-team-section github-section">
                <div class="project-team-section-heading"><p>GitHub repository</p><button v-if="project.github && !editingGithub" class="project-team-edit" type="button" @click="editingGithub = true">Change repository</button></div>
                <Transition name="github-choice"><div v-if="!project.github && !editingGithub && !creatingGithub" class="github-choice"><button type="button" @click="creatingGithub = true"><b>Create new repository</b><span>Private repository in the connected organization</span></button><button type="button" @click="editingGithub = true"><b>Link existing repository</b><span>Use a repository your team already has</span></button></div></Transition>
                <template v-if="editingGithub"><label class="github-field"><span>Repository URL</span><input v-model.trim="githubUrl" type="url" maxlength="300" placeholder="https://github.com/owner/repository" /></label><div class="project-team-actions"><button class="drawer-secondary" type="button" :disabled="saving" @click="cancelGithubEdit">Cancel</button><button v-if="project.github" class="project-delete-button" type="button" :disabled="saving" @click="unlinkGithub">Unlink</button><button class="drawer-primary" type="button" :disabled="saving" @click="saveGithub">{{ saving ? 'Saving…' : 'Save repository' }}</button></div></template>
                <template v-else-if="creatingGithub"><label class="github-field"><span>New repository name</span><input v-model.trim="repositoryName" type="text" maxlength="100" placeholder="project-name" /></label><small class="github-create-help">Pomas will create a private repository in the connected organization.</small><div class="project-team-actions"><button class="drawer-secondary" type="button" :disabled="saving" @click="cancelGithubCreate">Cancel</button><button class="drawer-primary" type="button" :disabled="saving" @click="createGithub">{{ saving ? 'Creating…' : 'Create repository' }}</button></div></template>
                <div v-else-if="project.github" class="github-connected"><a :href="project.github.repository_url" target="_blank" rel="noopener">{{ project.github.repository_owner }}/{{ project.github.repository_name }} ↗</a><small>{{ project.github.connection_status }}<template v-if='project.github.connection_status !== "Connected"'> · Verify that Pomas can access it.</template></small><button v-if='project.github.connection_status !== "Connected"' class="project-team-edit github-verify" type="button" :disabled="saving" @click="verifyGithub">{{ saving ? "Verifying…" : "Verify connection" }}</button></div>
              </section>
              <section class="project-team-section" :class="{ 'is-editing': editingAdmins }">
                <div class="project-team-section-heading"><p>Project admins</p><button v-if="!editingAdmins" class="project-team-edit" type="button" :disabled="loadingTeam" @click="beginAdminEdit">Edit project admins</button></div>
                <template v-if="editingAdmins">
                  <UserPicker v-model="admins" :users="teamCandidates" :locked-users="[owner]" label="Project admins" help="Use Add user to promote an existing team member. The Project owner always remains an admin." />
                  <div class="project-team-actions"><button class="drawer-secondary" type="button" :disabled="saving" @click="cancelAdminEdit">Cancel</button><button class="drawer-primary" type="button" :disabled="saving" @click="saveAdmins">Done</button></div>
                </template>
                <div v-else-if="!loadingTeam" class="project-team-members"><span v-for="admin in admins" :key="admin"><i>{{ memberInitials(admin) }}</i><b>{{ memberLabel(admin) }}<small v-if="admin === owner">Owner</small></b></span></div>
                <p v-else class="project-team-summary">Loading project admins…</p>
              </section>
              <section class="project-team-section" :class="{ 'is-editing': editingMembers }">
                <div class="project-team-section-heading"><p>Team members</p><button v-if="!editingMembers" class="project-team-edit" type="button" :disabled="loadingTeam" @click="beginTeamEdit">Edit team members</button></div>
                <template v-if="editingMembers">
                  <UserPicker v-model="members" :users="teamCandidates" label="Project access" help="Use Add user to grant access or the trash icon to remove access. The Project owner always remains a member." />
                  <div class="project-team-actions"><button class="drawer-secondary" type="button" :disabled="saving" @click="cancelTeamEdit">Cancel</button><button class="drawer-primary" type="button" :disabled="saving || loadingTeam" @click="saveTeam">{{ saving ? 'Saving…' : 'Done' }}</button></div>
                </template>
                <div v-else-if="!loadingTeam" class="project-team-members"><span v-for="member in members" :key="member"><i>{{ memberInitials(member) }}</i><b>{{ memberLabel(member) }}</b></span><p v-if="!members.length">No team members added yet.</p></div>
                <p v-else class="project-team-summary">Loading team members…</p>
              </section>
            </div>
            <p v-if="teamError" class="project-action-error" role="alert">{{ teamError }}</p>
            <footer><button class="drawer-primary" type="button" :disabled="saving" @click="closeTeam">Close</button></footer>
          </section>
        </div>
      </Transition>

      <Transition name="project-delete-pop">
        <div v-if="deleteOpen" class="project-delete-backdrop" role="dialog" aria-modal="true" aria-labelledby="delete-project-title" @click.self="closeDelete">
          <section class="project-delete-modal">
            <header><div class="project-delete-icon">!</div><div><p>Danger zone</p><h2 id="delete-project-title">Delete this Project?</h2></div><button type="button" aria-label="Close" @click="closeDelete">×</button></header>
            <p>This permanently deletes <strong>{{ project.project_name }}</strong>, its {{ project.task_count }} {{ project.task_count === 1 ? 'task' : 'tasks' }}, submitted work, and uploaded work files. This cannot be undone.</p>
            <label><span>Type <b>{{ project.project_name }}</b> to confirm</span><input v-model="confirmation" :placeholder="project.project_name" autocomplete="off" /></label>
            <p v-if="deleteError" class="project-action-error" role="alert">{{ deleteError }}</p>
            <footer><button class="drawer-secondary" type="button" :disabled="saving" @click="closeDelete">Cancel</button><button class="project-delete-button" type="button" :disabled="saving || confirmation !== project.project_name" @click="deleteProject">{{ saving ? 'Deleting…' : 'Permanently delete project' }}</button></footer>
          </section>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import UserPicker from "./UserPicker.vue"
import { callPms, uploadPms, type ProjectSummary, type TaskFormMember } from "../services/api"

const props = defineProps<{ project: ProjectSummary }>()
const emit = defineEmits<{ changed: []; deleted: [project: string] }>()
const root = ref<HTMLElement | null>(null)
const menuOpen = ref(false)
const teamOpen = ref(false)
const deleteOpen = ref(false)
const loadingTeam = ref(false)
const saving = ref(false)
const logoInput = ref<HTMLInputElement | null>(null)
const actionError = ref("")
const teamError = ref("")
const editingGithub = ref(false)
const creatingGithub = ref(false)
const repositoryName = ref("")
const githubUrl = ref("")
const editingMembers = ref(false)
const editingAdmins = ref(false)
const savedMembers = ref<string[]>([])
const savedAdmins = ref<string[]>([])
const admins = ref<string[]>([])
const owner = ref("")
const deleteError = ref("")
const members = ref<string[]>([])
const candidates = ref<TaskFormMember[]>([])
const confirmation = ref("")

const teamCandidates = computed(() => candidates.value.filter((candidate) => candidate.name !== owner.value && !admins.value.includes(candidate.name)))
function outside(event: MouseEvent) { if (root.value && !root.value.contains(event.target as Node)) menuOpen.value = false }
function openLogoPicker() { actionError.value = ""; logoInput.value?.click() }
async function uploadLogo(event: Event) { const logo = (event.target as HTMLInputElement).files?.[0]; if (!logo) return; saving.value = true; actionError.value = ""; try { const data = new FormData(); data.append("project", props.project.name); data.append("logo", logo, logo.name); await uploadPms("pms.api.upload_project_logo", data); menuOpen.value = false; emit("changed") } catch (reason) { actionError.value = reason instanceof Error ? reason.message : "Unable to save the Project logo." } finally { saving.value = false; if (logoInput.value) logoInput.value.value = "" } }
function onKey(event: KeyboardEvent) { if (event.key === "Escape") { menuOpen.value = false; if (!saving.value) { teamOpen.value = false; deleteOpen.value = false } } }
onMounted(() => { document.addEventListener("click", outside); document.addEventListener("keydown", onKey) })
onBeforeUnmount(() => { document.removeEventListener("click", outside); document.removeEventListener("keydown", onKey) })

async function complete() {
  saving.value = true
  try { await callPms("pms.api.complete_project", { project: props.project.name }); menuOpen.value = false; emit("changed") }
  finally { saving.value = false }
}
function openEditProject() { void openTeam() }
async function openTeam() {
  menuOpen.value = false; teamError.value = ""; editingMembers.value = false; editingAdmins.value = false; editingGithub.value = false; creatingGithub.value = false; repositoryName.value = ""; githubUrl.value = props.project.github?.repository_url || ""; teamOpen.value = true; loadingTeam.value = true
  try { const result = await callPms<{ owner: string; admins: string[]; members: string[]; candidates: TaskFormMember[] }>("pms.api.get_project_members", { project: props.project.name }); owner.value = result.owner; admins.value = result.admins; savedAdmins.value = [...result.admins]; members.value = result.members; savedMembers.value = [...result.members]; candidates.value = result.candidates }
  catch (reason) { teamError.value = reason instanceof Error ? reason.message : "Unable to load the Project team." }
  finally { loadingTeam.value = false }
}
function closeTeam() { if (!saving.value) { editingMembers.value = false; editingAdmins.value = false; editingGithub.value = false; creatingGithub.value = false; teamOpen.value = false } }
function memberLabel(member: string) { return candidates.value.find((candidate) => candidate.name === member)?.full_name || member }
function memberInitials(member: string) { return memberLabel(member).split(/[@.\s]+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("") }
function cancelGithubCreate() { repositoryName.value = ""; creatingGithub.value = false }
async function createGithub() { teamError.value = ""; saving.value = true; try { await callPms("pms.api.create_project_github_repository", { project: props.project.name, repository_name: repositoryName.value }); repositoryName.value = ""; creatingGithub.value = false; emit("changed") } catch (reason) { teamError.value = reason instanceof Error ? reason.message : "Unable to create this GitHub repository." } finally { saving.value = false } }
function beginAdminEdit() { teamError.value = ""; editingAdmins.value = true }
function cancelAdminEdit() { admins.value = [...savedAdmins.value]; teamError.value = ""; editingAdmins.value = false }
async function saveAdmins() {
  teamError.value = ""; saving.value = true
  try {
    const before = new Set(savedAdmins.value.filter((member) => member !== owner.value))
    const after = new Set(admins.value.filter((member) => member !== owner.value))
    for (const member of after) if (!before.has(member)) await callPms("pms.api.set_project_member_role", { project: props.project.name, member, project_role: "Project Manager" })
    for (const member of before) if (!after.has(member)) await callPms("pms.api.set_project_member_role", { project: props.project.name, member, project_role: "Member" })
    await openTeam(); emit("changed")
  } catch (reason) { teamError.value = reason instanceof Error ? reason.message : "Unable to update project admins." }
  finally { saving.value = false }
}
function beginTeamEdit() { teamError.value = ""; editingMembers.value = true }
function cancelTeamEdit() { members.value = [...savedMembers.value]; teamError.value = ""; editingMembers.value = false }
function cancelGithubEdit() { githubUrl.value = props.project.github?.repository_url || ""; editingGithub.value = false }
async function saveGithub() { teamError.value = ""; saving.value = true; try { await callPms("pms.api.link_project_github_repository", { project: props.project.name, repository_url: githubUrl.value }); editingGithub.value = false; emit("changed") } catch (reason) { teamError.value = reason instanceof Error ? reason.message : "Unable to link this GitHub repository." } finally { saving.value = false } }
async function unlinkGithub() { teamError.value = ""; saving.value = true; try { await callPms("pms.api.unlink_project_github_repository", { project: props.project.name }); githubUrl.value = ""; editingGithub.value = false; emit("changed") } catch (reason) { teamError.value = reason instanceof Error ? reason.message : "Unable to unlink this GitHub repository." } finally { saving.value = false } }
async function verifyGithub() { teamError.value = ""; saving.value = true; try { await callPms("pms.api.verify_project_github_repository", { project: props.project.name }); emit("changed") } catch (reason) { teamError.value = reason instanceof Error ? reason.message : "Unable to verify this GitHub repository." } finally { saving.value = false } }
async function saveTeam() { teamError.value = ""; saving.value = true; try { await callPms("pms.api.update_project_members", { project: props.project.name, members: [...members.value, ...admins.value] }); savedMembers.value = [...members.value]; editingMembers.value = false; emit("changed") } catch (reason) { teamError.value = reason instanceof Error ? reason.message : "Unable to save the Project team." } finally { saving.value = false } }
function openDelete() { menuOpen.value = false; confirmation.value = ""; deleteError.value = ""; deleteOpen.value = true }
function closeDelete() { if (!saving.value) deleteOpen.value = false }
async function deleteProject() { deleteError.value = ""; saving.value = true; try { await callPms("pms.api.delete_project", { project: props.project.name, confirmation: confirmation.value }); deleteOpen.value = false; emit("deleted", props.project.name) } catch (reason) { deleteError.value = reason instanceof Error ? reason.message : "Unable to delete this Project." } finally { saving.value = false } }
</script>

<style scoped>
.project-logo-native{display:none}
.github-choice{display:grid;gap:8px;margin-top:13px}.github-choice button{display:grid;gap:3px;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--text-2);text-align:left;cursor:pointer}.github-choice button:hover{border-color:var(--c-violet);background:var(--c-lavender)}.github-choice b{font-size:11px}.github-choice span,.github-create-help{color:var(--muted);font-size:10px}.github-create-help{display:block;margin-top:8px}.github-choice-enter-active,.github-choice-leave-active{transition:opacity .18s ease,transform .18s ease}.github-choice-enter-from,.github-choice-leave-to{opacity:0;transform:translateY(-6px)}[data-theme=dark] .github-choice button{border-color:var(--d-line);background:var(--d-surface-2);color:var(--d-title)}[data-theme=dark] .github-choice button:hover{background:var(--d-hover)}
.project-actions{position:relative;z-index:4}.project-actions-trigger{display:grid;place-items:center;width:32px;height:32px;padding:0;border:1px solid transparent;border-radius:8px;background:transparent;color:var(--muted);font-size:0;cursor:pointer}.project-actions-trigger::before{display:block;content:"•••";font-size:15px;font-weight:900;letter-spacing:1px;line-height:1;transform:translateY(1px)}.project-actions-trigger:hover,.project-actions-trigger[aria-expanded=true]{border-color:var(--sb-active);background:var(--sb-active);color:white}.project-actions-popover{position:absolute;top:37px;right:0;z-index:20;width:180px;display:grid;gap:2px;padding:6px;border:1px solid var(--line);border-radius:10px;background:white;box-shadow:0 14px 32px rgba(12,9,20,.18)}.project-actions-popover button{width:100%;padding:9px;border:0;border-radius:7px;background:transparent;color:var(--text-2);font-size:11px;font-weight:750;text-align:left;cursor:pointer}.project-actions-popover button:hover{background:color-mix(in srgb,var(--c-violet) 18%,var(--c-lavender));color:var(--c-violet)}.project-actions-popover .project-actions-danger{margin-top:3px;border-top:1px solid var(--line-soft);border-radius:0;color:#be4350}.project-actions-popover .project-actions-danger:hover{background:#fff0f1;color:#a52f3d}.project-actions-pop-enter-active,.project-actions-pop-leave-active{transition:opacity .14s ease,transform .14s ease}.project-actions-pop-enter-from,.project-actions-pop-leave-to{opacity:0;transform:translateY(-4px) scale(.98)}.project-team-drawer{position:fixed;inset:0;z-index:500;display:flex;justify-content:flex-end}.project-team-backdrop{position:absolute;inset:0;border:0;background:rgba(8,9,12,.58);backdrop-filter:blur(3px)}.project-team-panel{position:relative;z-index:1;width:min(520px,96vw);height:100%;display:flex;flex-direction:column;overflow-y:auto;padding:28px;background:var(--bg);color:var(--text-2);box-shadow:-18px 0 48px rgba(0,0,0,.25)}.project-team-header{display:flex;justify-content:space-between;gap:18px;padding-bottom:20px;border-bottom:1px solid var(--line)}.project-team-header p,.project-delete-modal header p{margin:0;color:var(--c-violet);font-size:10px;font-weight:850;letter-spacing:.11em;text-transform:uppercase}.project-team-header h2,.project-delete-modal h2{margin:6px 0;color:var(--c-ink);font-size:24px;letter-spacing:-.035em}.project-team-header span{color:var(--muted);font-size:12px;line-height:1.45}.project-team-header>button,.project-delete-modal header>button{width:34px;height:34px;flex:0 0 auto;border:1px solid var(--line);border-radius:9px;background:white;color:var(--text-2);font-size:20px;cursor:pointer}.project-team-content{padding:23px 0}.project-team-panel footer,.project-delete-modal footer{display:flex;justify-content:flex-end;gap:9px;margin-top:auto;padding-top:18px;border-top:1px solid var(--line)}.drawer-primary,.drawer-secondary,.project-delete-button{min-height:40px;padding:0 15px;border-radius:9px;font-size:12px;font-weight:800;cursor:pointer}.drawer-primary{border:1px solid var(--c-violet);background:var(--c-violet);color:white}.drawer-secondary{border:1px solid var(--line);background:white;color:var(--text-2)}.project-action-error{margin:0 0 16px;padding:10px 11px;border:1px solid #ffd2d6;border-radius:9px;background:#fff0f1;color:#b83f4a;font-size:11px;line-height:1.45}.project-delete-backdrop{position:fixed;inset:0;z-index:550;display:grid;place-items:center;padding:20px;background:rgba(8,9,12,.58);backdrop-filter:blur(3px)}.project-delete-modal{width:min(480px,100%);padding:25px;border:1px solid var(--line);border-radius:16px;background:white;color:var(--text-2);box-shadow:0 24px 60px rgba(0,0,0,.3)}.project-delete-modal header{display:flex;align-items:flex-start;gap:12px}.project-delete-modal header>div:nth-child(2){min-width:0;flex:1}.project-delete-icon{display:grid;place-items:center;width:36px;height:36px;flex:0 0 auto;border-radius:10px;background:#fff0f1;color:#bb3f4d;font-size:20px;font-weight:900}.project-delete-modal>p{margin:19px 0;color:var(--muted);font-size:12px;line-height:1.6}.project-delete-modal>p strong{color:var(--text-2)}.project-delete-modal label{display:grid;gap:7px;color:var(--text-2);font-size:11px;font-weight:750}.project-delete-modal label b{color:#b83f4a}.project-delete-modal input{width:100%;height:42px;padding:0 11px;border:1px solid var(--line);border-radius:9px;background:white;color:var(--c-ink);outline:none}.project-delete-modal input:focus{border-color:#b83f4a;box-shadow:0 0 0 3px rgba(184,63,74,.13)}.project-delete-button{border:1px solid #b83f4a;background:#b83f4a;color:white}.project-delete-button:disabled,.drawer-primary:disabled,.drawer-secondary:disabled{cursor:not-allowed;opacity:.55}.side-drawer-enter-active,.side-drawer-leave-active,.project-delete-pop-enter-active,.project-delete-pop-leave-active{transition:opacity .18s}.side-drawer-enter-active .project-team-panel,.side-drawer-leave-active .project-team-panel{transition:transform .2s}.side-drawer-enter-from,.side-drawer-leave-to,.project-delete-pop-enter-from,.project-delete-pop-leave-to{opacity:0}.side-drawer-enter-from .project-team-panel,.side-drawer-leave-to .project-team-panel{transform:translateX(28px)}[data-theme=dark] .project-actions-popover,[data-theme=dark] .project-team-panel,[data-theme=dark] .project-delete-modal,[data-theme=dark] .project-team-header>button,[data-theme=dark] .project-delete-modal header>button,[data-theme=dark] .drawer-secondary,[data-theme=dark] .project-delete-modal input{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .project-actions-popover button{color:var(--c-lavender)}[data-theme=dark] .project-actions-popover button:hover{background:var(--d-hover);color:var(--c-orchid)}[data-theme=dark] .project-actions-popover .project-actions-danger{border-color:var(--d-line);color:#ffabb4}[data-theme=dark] .project-team-header,[data-theme=dark] .project-team-panel footer,[data-theme=dark] .project-delete-modal footer{border-color:var(--d-line)}[data-theme=dark] .project-team-header h2,[data-theme=dark] .project-delete-modal h2,[data-theme=dark] .project-delete-modal>p strong{color:var(--d-title)}[data-theme=dark] .project-team-header span,[data-theme=dark] .project-delete-modal>p{color:var(--d-muted)}[data-theme=light] .project-actions-trigger:hover,[data-theme=light] .project-actions-trigger[aria-expanded=true]{border-color:var(--c-violet);background:var(--c-violet);color:white}[data-theme=dark] .project-delete-icon{background:#35181f;color:#ffb8c0}[data-theme=dark] .project-action-error{border-color:#5c2631;background:#35181f;color:#ffb8c0}@media(max-width:600px){.project-team-panel{width:100%;padding:22px 18px}.project-delete-modal{padding:20px}.project-delete-modal footer{flex-direction:column-reverse}.project-delete-modal footer button{width:100%}}
.project-logo-section{padding-bottom:22px}.project-logo-section>p,.project-team-section>p{margin:0 0 11px;color:var(--text-2);font-size:12px;font-weight:850}.project-logo-control{display:flex;align-items:center;gap:14px}.project-logo-drop{display:grid;place-items:center;width:96px;height:96px;flex:0 0 auto;padding:0;overflow:hidden;border:2px dashed var(--line);border-radius:14px;background:color-mix(in srgb,var(--c-lavender) 35%,white);color:var(--c-violet);font-size:34px;font-weight:400;cursor:pointer}.project-logo-drop:hover{border-color:var(--c-violet);background:color-mix(in srgb,var(--c-lavender) 58%,white)}.project-logo-drop img{width:100%;height:100%;object-fit:cover}.project-logo-control>div{display:grid;gap:7px}.project-logo-control strong{color:var(--c-ink);font-size:13px}.project-logo-change{width:max-content;padding:0;border:0;background:transparent;color:var(--c-violet);font-size:12px;font-weight:800;cursor:pointer}.project-logo-section small{display:block;margin-top:9px;color:var(--muted);font-size:10px}.project-team-section{padding-top:20px;border-top:1px solid var(--line)}[data-theme=dark] .project-logo-drop{border-color:var(--d-line);background:var(--d-hover);color:var(--c-orchid)}[data-theme=dark] .project-logo-drop:hover{border-color:var(--c-orchid);background:#2a1f3c}[data-theme=dark] .project-logo-control strong,[data-theme=dark] .project-team-section>p,[data-theme=dark] .project-logo-section>p{color:var(--d-title)}[data-theme=dark] .project-logo-section small{color:var(--d-muted)}[data-theme=dark] .project-team-section{border-color:var(--d-line)}
.project-team-section-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.project-team-edit{min-height:32px;padding:0 10px;border:1px solid var(--c-violet);border-radius:8px;background:transparent;color:var(--c-violet);font-size:10px;font-weight:850;cursor:pointer}.project-team-edit:hover{background:var(--c-lavender)}.project-team-edit:disabled{cursor:not-allowed;opacity:.55}.project-team-summary{margin:0;padding:13px;border:1px dashed var(--line);border-radius:10px;color:var(--muted);font-size:11px;text-align:center}.project-team-actions{display:flex;justify-content:flex-end;gap:9px;margin-top:16px}
.project-team-members{display:flex;flex-wrap:wrap;gap:7px}.project-team-members>span{display:flex;align-items:center;gap:7px;min-height:34px;padding:4px 8px 4px 6px;border:1px solid var(--line);border-radius:9px;background:var(--line-soft);color:var(--text-2);font-size:10px}.project-team-members i{display:grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--c-lavender);color:var(--c-plum);font-size:7px;font-style:normal;font-weight:850}.project-team-members p{width:100%;margin:0;padding:13px;border:1px dashed var(--line);border-radius:10px;color:var(--muted);font-size:11px;text-align:center}[data-theme=dark] .project-team-members>span,.project-team-members p{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}
.project-team-section{margin-top:4px;padding:18px;border:1px solid var(--line);border-radius:13px;background:color-mix(in srgb,var(--c-lavender) 12%,white)}.project-team-section-heading{padding-bottom:12px;border-bottom:1px solid var(--line)}.project-team-section-heading p{margin:0;color:var(--c-ink);font-size:13px;font-weight:850}.project-team-section .user-picker{margin-top:15px}[data-theme=dark] .project-team-section{border-color:var(--d-line);background:var(--d-surface-2)}[data-theme=dark] .project-team-section-heading{border-color:var(--d-line)}[data-theme=dark] .project-team-section-heading p{color:var(--d-title)}
.project-team-section.is-editing{background:var(--c-lavender)}[data-theme=dark] .project-team-section.is-editing{background:var(--d-hover)}
.project-team-section:not(.github-section) .project-team-edit{border-color:var(--line);background:white;color:var(--text-2);box-shadow:none}.project-team-section:not(.github-section) .project-team-edit:hover{border-color:var(--line);background:var(--line-soft);color:var(--text-2)}[data-theme=dark] .project-team-section:not(.github-section) .project-team-edit{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .project-team-section:not(.github-section) .project-team-edit:hover{background:var(--d-hover);color:var(--c-lavender)}
.github-verify{width:max-content;margin-top:7px}
.github-section{margin-top:4px}.github-field{display:grid;gap:7px;margin-top:14px;color:var(--text-2);font-size:11px;font-weight:800}.github-field input{width:100%;min-height:42px;padding:0 11px;border:1px solid var(--line);border-radius:9px;background:white;color:var(--c-ink);outline:none}.github-field input:focus{border-color:var(--c-violet);box-shadow:0 0 0 3px color-mix(in srgb,var(--c-violet) 16%,transparent)}.github-connected{display:grid;gap:5px;margin-top:13px}.github-connected a{width:max-content;max-width:100%;overflow:hidden;color:var(--c-violet);font-size:12px;font-weight:850;text-decoration:none;text-overflow:ellipsis;white-space:nowrap}.github-connected a:hover{text-decoration:underline}.github-connected small{color:var(--muted);font-size:10px}[data-theme=dark] .github-field{color:var(--c-lavender)}[data-theme=dark] .github-field input{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .github-connected small{color:var(--d-muted)}
.project-admin-add{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:9px;margin-top:14px}.project-admin-add .drawer-primary{min-height:43px}.project-team-section-heading+.project-team-members{margin-top:14px}.project-admin-add+.project-team-members{margin-top:14px}.project-team-section-heading+ .project-team-summary{margin-top:14px}
.project-role-action{margin-left:3px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;background:transparent;color:var(--c-violet);font-size:9px;font-weight:800;cursor:pointer}.project-team-members small{display:block;color:var(--muted);font-size:8px}.project-role-action:disabled{opacity:.55;cursor:not-allowed}[data-theme=dark] .project-role-action{border-color:var(--d-line);color:var(--c-orchid)}
.project-team-drawer .project-action-error{position:fixed;z-index:800;top:18px;left:50%;width:min(460px,calc(100vw - 32px));margin:0;transform:translateX(-50%);box-shadow:0 14px 34px rgba(12,9,20,.22)}
.project-team-panel .project-action-error{position:absolute;z-index:12;top:92px;left:18px;right:18px;width:auto;margin:0;transform:none;animation:project-error-drop .18s ease-out}@keyframes project-error-drop{from{opacity:0;transform:translateY(-9px)}to{opacity:1;transform:translateY(0)}}
</style>
