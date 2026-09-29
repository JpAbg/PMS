<template>
  <div ref="root" :class="['profile-menu', `profile-menu--${variant}`]">
    <button
      class="profile-trigger"
      type="button"
      :aria-expanded="menuOpen"
      aria-haspopup="menu"
      @click="menuOpen = !menuOpen"
    >
      <span class="profile-avatar">
        <img
          v-if="session.user_image && !imageFailed"
          :src="session.user_image"
          :alt="`${session.full_name}'s profile picture`"
          @error="imageFailed = true"
        />
        <span v-else>{{ initials(session.full_name) }}</span>
      </span>
      <span class="profile-copy">
        <strong>{{ session.full_name }}</strong>
        <small>{{ roleLabel }}</small>
      </span>
      <svg class="profile-chevron" viewBox="0 0 24 24" aria-hidden="true">
        <path d="m7 10 5 5 5-5" />
      </svg>
    </button>

    <Transition name="profile-pop">
      <div v-if="menuOpen" class="profile-dropdown" role="menu">
        <button type="button" role="menuitem" @click="openDialog('about')">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 11v6M12 7.5h.01" />
          </svg>
          <span>About Pomas</span>
        </button>
        <button type="button" role="menuitem" @click="openSettings">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path d="M19 13.5v-3l-2-.7-.7-1.7.9-1.9-2.1-2.1-1.9.9-1.7-.7L10.5 2h-3l-.7 2.3-1.7.7-1.9-.9-2.1 2.1.9 1.9-.7 1.7-2 .7v3l2 .7.7 1.7-.9 1.9 2.1 2.1 1.9-.9 1.7.7.7 2.3h3l.7-2.3 1.7-.7 1.9.9 2.1-2.1-.9-1.9.7-1.7 2-.7Z" transform="translate(2)" />
          </svg>
          <span>Settings</span>
        </button>
        <button class="profile-logout" type="button" role="menuitem" :disabled="loggingOut" @click="logout">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m10 17 5-5-5-5M15 12H3" />
            <path d="M14 3h6a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1h-6" />
          </svg>
          <span>{{ loggingOut ? "Logging out…" : "Log out" }}</span>
        </button>
        <p v-if="menuError" class="profile-menu-error">{{ menuError }}</p>
      </div>
    </Transition>

    <Teleport to="body">
      <div v-if="dialog" class="profile-modal-backdrop" @click.self="dialog = null">
        <section class="profile-modal" role="dialog" aria-modal="true" :aria-labelledby="`profile-${dialog}-title`">
          <header class="profile-modal-header"><div><p class="eyebrow">{{ dialog === "about" ? "About" : "Settings" }}</p><h2 :id="`profile-${dialog}-title`">{{ dialog === "about" ? "Pomas" : "Workspace settings" }}</h2></div><button class="profile-modal-close" type="button" aria-label="Close" @click="dialog = null">×</button></header>

          <template v-if="dialog === 'about'">
            <p>Plan projects, organize work, and follow ERPNext tasks through one focused workspace.</p>
          </template>

          <template v-else>
            <nav class="settings-tabs"><button :class="{active: settingsSection === 'account'}" @click="settingsSection = 'account'">Account</button><button :class="{active: settingsSection === 'appearance'}" @click="settingsSection = 'appearance'">Appearance</button><button :class="{active: settingsSection === 'workspace'}" @click="settingsSection = 'workspace'">Workspace</button><button v-if="session.can_manage_github" :class="{active: settingsSection === 'github'}" @click="openGithubSettings">GitHub</button></nav>
            <section v-if="settingsSection === 'account'" class="settings-section"><dl class="profile-account-details"><div><dt>Name</dt><dd>{{ session.full_name }}</dd></div><div><dt>Account</dt><dd>{{ session.user }}</dd></div><div><dt>Access</dt><dd>{{ roleLabel }}</dd></div></dl></section>
            <section v-else-if="settingsSection === 'appearance'" class="settings-section"><p>Choose the Pomas color mode for this browser.</p><div class="profile-theme-options"><button type="button" :class="{ active: theme === 'light' }" @click="setTheme('light')">☀ Light</button><button type="button" :class="{ active: theme === 'dark' }" @click="setTheme('dark')">☾ Dark</button></div></section>
            <section v-else-if="settingsSection === 'workspace'" class="settings-section"><p>Your workspace keeps its compact navigation preference. Press <b>Ctrl + B</b> to open or close the sidebar.</p><div class="settings-note"><b>Shortcuts</b><span>Escape closes panels and dialogs.</span></div></section>
            <section v-else class="settings-section"><p>Choose whether projects use the current Pomas GitHub connection or connect an existing organization.</p><div v-if="githubLoading" class="settings-note">Loading GitHub connection…</div><template v-else><div v-if="!githubMode" class="github-choice"><button type="button" @click="githubMode = 'current'"><b>Use current connection</b><span>{{ github.organization ? github.organization : 'No organization connected yet' }}</span></button><button type="button" @click="githubMode = 'existing'"><b>Connect existing organization</b><span>Enter that organization’s GitHub App details</span></button></div><Transition name="github-choice"><div v-if="githubMode === 'current'" class="github-settings-panel"><b>{{ github.enabled ? 'Connected organization: ' + github.organization : 'No active GitHub connection' }}</b><div class="project-team-actions"><button class="drawer-secondary" type="button" @click="githubMode = null">Back</button><button class="drawer-primary" type="button" :disabled="githubSaving || !github.enabled" @click="testGithub">{{ githubSaving ? 'Testing…' : 'Test connection' }}</button></div></div><div v-else-if="githubMode === 'existing'" class="github-settings-panel"><label>Organization<input v-model.trim="github.organization" placeholder="your-organization" /></label><label>GitHub App ID<input v-model.trim="github.app_id" inputmode="numeric" /></label><label>Installation ID<input v-model.trim="github.installation_id" inputmode="numeric" /></label><label>Private key<input v-model="githubPrivateKey" type="password" placeholder="PEM or Base64 PEM" /></label><small>Stored encrypted on the server. Never paste it into chat.</small><div class="project-team-actions"><button class="drawer-primary" type="button" :disabled="githubSaving" @click="saveGithubSettings">{{ githubSaving ? 'Saving…' : 'Save connection' }}</button></div></div></Transition><p v-if="githubError" class="project-action-error">{{ githubError }}</p><p v-if="githubStatus" class="settings-success">{{ githubStatus }}</p></template></section>
          </template>
        </section>
      </div>
    </Teleport>
  </div>
    <Teleport to="body"><Transition name="side-drawer"><div v-if="settingsOpen" class="pomas-settings-drawer" role="dialog" aria-modal="true" aria-labelledby="pomas-settings-title"><button class="pomas-settings-backdrop" type="button" aria-label="Close settings" @click="settingsOpen = false" /><section class="pomas-settings-panel"><header><div><p>Preferences</p><h2 id="pomas-settings-title">Settings</h2><span>Personalize how Pomas looks and behaves.</span></div><button type="button" aria-label="Close" @click="settingsOpen = false">×</button></header><section><h3>Appearance</h3><div class="pomas-setting-row"><div><strong>Theme</strong><small>Choose light or dark for this browser.</small></div><div class="pomas-segment"><button :class="{active: theme === 'light'}" @click="setTheme('light')">☀ Light</button><button :class="{active: theme === 'dark'}" @click="setTheme('dark')">☾ Dark</button></div></div></section><section><h3>Sidebar</h3><div class="pomas-setting-row"><div><strong>Start collapsed</strong><small>Apply this preference when Pomas next opens.</small></div><label class="pomas-switch"><input v-model="sidebarDefault" type="checkbox" @change="saveSidebarPreference" /><span /></label></div></section><section><h3>Workspace</h3><div class="pomas-setting-row"><div><strong>Keyboard shortcuts</strong><small>Ctrl + B toggles the sidebar. Escape closes panels.</small></div><b class="pomas-key">Ctrl B</b></div></section><section v-if="session.can_manage_github"><h3>GitHub organization</h3><div class="pomas-setting-row pomas-setting-row--stack"><div><strong>{{ github.enabled ? github.organization : 'No organization connected' }}</strong><small>The active organization used when Pomas creates or links project repositories.</small></div><button class="pomas-update-connection" type="button" @click="openGithubSettings(); githubMode = 'existing'">Update connection</button><Transition name="github-choice"><div v-if="false" class="pomas-connection-form"><b>{{ github.enabled ? 'Connected to ' + github.organization : 'No active connection' }}</b><div class="project-team-actions"><button class="drawer-secondary" type="button" @click="githubMode = null">Back</button><button class="drawer-primary" :disabled="githubSaving || !github.enabled" type="button" @click="testGithub">{{ githubSaving ? 'Testing…' : 'Test connection' }}</button></div></div><div v-else-if="githubMode === 'existing'" class="pomas-connection-form"><label>Organization<input v-model.trim="github.organization" /></label><label>GitHub App ID<input v-model.trim="github.app_id" /></label><label>Installation ID<input v-model.trim="github.installation_id" /></label><label>Private key<input v-model="githubPrivateKey" type="password" placeholder="PEM or Base64 PEM" /></label><small>Encrypted on the server; never paste it into chat.</small><div class="project-team-actions"><button class="drawer-secondary" type="button" @click="githubMode = null">Cancel</button><button class="drawer-primary" :disabled="githubSaving" type="button" @click="saveGithubSettings">{{ githubSaving ? 'Saving…' : 'Save connection' }}</button></div></div></Transition><p v-if="githubError" class="project-action-error">{{ githubError }}</p><p v-if="githubStatus" class="settings-success">{{ githubStatus }}</p></div></section><footer><button class="drawer-secondary" type="button" @click="settingsOpen = false">Close</button></footer></section></div></Transition></Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { callPms, type PmsSession } from "../services/api"
import { setTheme, theme } from "../services/theme"

const props = withDefaults(defineProps<{ session: PmsSession; variant?: "sidebar" | "mobile" }>(), {
  variant: "sidebar",
})
const emit = defineEmits<{ menuChange: [open: boolean] }>()

const root = ref<HTMLElement | null>(null)
const menuOpen = ref(false)
const dialog = ref<"about" | "settings" | null>(null)
const loggingOut = ref(false)
const menuError = ref("")
const imageFailed = ref(false)
const roleLabel = computed(() => props.session.roles[0] || (props.session.is_administrator ? "Administrator" : "Pomas member"))
const settingsSection = ref<"account" | "appearance" | "workspace" | "github">("account")
const githubMode = ref<"current" | "existing" | null>(null)
const githubLoading = ref(false)
const settingsOpen = ref(false)
const sidebarDefault = ref(false)
const githubSaving = ref(false)
const githubError = ref("")
const githubStatus = ref("")
const githubPrivateKey = ref("")
const github = ref({ enabled: false, app_id: "", installation_id: "", organization: "" })

watch(menuOpen, (open) => emit("menuChange", open))

function initials(value: string) { return value.split(/[@.\s]+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("") }
function openDialog(value: "about" | "settings") { menuOpen.value = false; dialog.value = value; if (value === "settings") settingsSection.value = "account" }
async function openGithubSettings() { settingsSection.value = "github"; githubMode.value = null; githubError.value = ""; githubStatus.value = ""; githubLoading.value = true; try { github.value = await callPms<typeof github.value>("pms.api.get_github_connection_settings") } catch (reason) { githubError.value = reason instanceof Error ? reason.message : "Unable to load GitHub settings." } finally { githubLoading.value = false } }
async function saveGithubSettings() { githubError.value = ""; githubSaving.value = true; try { github.value = await callPms<typeof github.value>("pms.api.save_github_connection_settings", { enabled: true, ...github.value, private_key: githubPrivateKey.value }); githubPrivateKey.value = ""; githubMode.value = "current"; githubStatus.value = "GitHub organization saved." } catch (reason) { githubError.value = reason instanceof Error ? reason.message : "Unable to save GitHub settings." } finally { githubSaving.value = false } }
function openSettings() { menuOpen.value = false; sidebarDefault.value = window.localStorage.getItem("pomas-sidebar-collapsed") === "1"; settingsOpen.value = true; githubMode.value = null; githubError.value = ""; githubStatus.value = ""; if (props.session.can_manage_github) void openGithubSettings() }
function saveSidebarPreference() { window.localStorage.setItem("pomas-sidebar-collapsed", sidebarDefault.value ? "1" : "0") }
async function testGithub() { githubError.value = ""; githubStatus.value = ""; githubSaving.value = true; try { await callPms("pms.api.test_github_connection"); githubStatus.value = "Connection verified." } catch (reason) { githubError.value = reason instanceof Error ? reason.message : "Unable to test GitHub." } finally { githubSaving.value = false } }

function handleDocumentClick(event: MouseEvent) {
  if (!root.value?.contains(event.target as Node)) menuOpen.value = false
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") return
  menuOpen.value = false
  dialog.value = null
  settingsOpen.value = false
}

async function logout() {
  settingsOpen.value = false
  loggingOut.value = true
  menuError.value = ""
  try {
    await callPms("logout")
    window.location.assign("/pms/login")
  } catch (reason) {
    menuError.value = reason instanceof Error ? reason.message : "Unable to log out."
    loggingOut.value = false
  }
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick)
  document.addEventListener("keydown", handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick)
  document.removeEventListener("keydown", handleKeydown)
})
</script>

<style scoped>
.settings-tabs{display:flex;gap:6px;flex-wrap:wrap;margin:18px 0}.settings-tabs button{border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--muted);padding:7px 10px;font-size:11px;font-weight:800;cursor:pointer}.settings-tabs button.active{border-color:var(--c-violet);background:var(--c-violet);color:white}.settings-section{display:grid;gap:13px;min-height:160px}.settings-section>p{margin:0;color:var(--muted);font-size:12px;line-height:1.55}.settings-note,.github-settings-panel{display:grid;gap:8px;padding:13px;border:1px solid var(--line);border-radius:10px;background:var(--line-soft);color:var(--text-2);font-size:11px}.github-settings-panel label{display:grid;gap:5px;color:var(--text-2);font-size:10px;font-weight:800}.github-settings-panel input{height:38px;padding:0 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--text-2)}.github-settings-panel small{color:var(--muted);font-size:10px}.settings-success{margin:0;color:var(--c-violet);font-size:11px;font-weight:800}[data-theme=dark] .settings-tabs button,[data-theme=dark] .github-settings-panel input{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .settings-note,[data-theme=dark] .github-settings-panel{border-color:var(--d-line);background:var(--d-hover);color:var(--d-title)}
</style>

<style scoped>
.pomas-settings-drawer{position:fixed;inset:0;z-index:700;display:flex;justify-content:flex-end}.pomas-settings-backdrop{position:absolute;inset:0;border:0;background:rgba(8,9,12,.58);backdrop-filter:blur(3px)}.pomas-settings-panel{position:relative;z-index:1;display:flex;flex-direction:column;width:min(560px,94vw);height:100%;overflow-y:auto;padding:26px;background:var(--bg);color:var(--text-2);box-shadow:-18px 0 44px rgba(0,0,0,.22)}.pomas-settings-panel header{display:flex;justify-content:space-between;gap:18px;padding-bottom:18px;border-bottom:1px solid var(--line)}.pomas-settings-panel header p{margin:0;color:var(--c-violet);font-size:10px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}.pomas-settings-panel h2{margin:6px 0;color:var(--c-ink);font-size:23px}.pomas-settings-panel header span{color:var(--muted);font-size:12px}.pomas-settings-panel header>button{width:36px;height:36px;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--c-violet);font-size:23px;cursor:pointer}.pomas-settings-panel>section{margin-top:20px}.pomas-settings-panel>section>h3{margin:0 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line);color:var(--text-2);font-size:13px}.pomas-setting-row{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:14px;border:1px solid var(--line);border-radius:13px;background:var(--line-soft)}.pomas-setting-row--stack{display:grid;align-items:stretch}.pomas-setting-row strong{display:block;color:var(--c-ink);font-size:13px}.pomas-setting-row small{display:block;margin-top:3px;color:var(--muted);font-size:11px;line-height:1.4}.pomas-segment{display:inline-flex;padding:3px;gap:2px;border:1px solid var(--line);border-radius:10px;background:var(--bg)}.pomas-segment button{padding:7px 12px;border:0;border-radius:7px;background:transparent;color:var(--muted);font-size:11px;font-weight:800;cursor:pointer}.pomas-segment button.active{background:var(--c-violet);color:white}.pomas-switch input{position:absolute;opacity:0}.pomas-switch span{display:block;width:42px;height:23px;border-radius:20px;background:#aab5a3;cursor:pointer}.pomas-switch span:after{display:block;width:17px;height:17px;margin:3px;border-radius:50%;background:white;content:"";transition:transform .16s}.pomas-switch input:checked+span{background:var(--c-violet)}.pomas-switch input:checked+span:after{transform:translateX(19px)}.pomas-key{padding:6px 9px;border:1px solid var(--line);border-radius:7px;background:var(--bg);font-size:10px}.pomas-connection-actions,.pomas-connection-form{display:flex;gap:9px;align-items:center;flex-wrap:wrap}.pomas-connection-form{display:grid;gap:10px;padding-top:4px}.pomas-connection-form label{display:grid;gap:5px;font-size:10px;font-weight:800}.pomas-connection-form input{height:39px;padding:0 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--text-2)}.pomas-settings-panel footer{display:flex;justify-content:flex-end;margin-top:24px;padding-top:18px;border-top:1px solid var(--line)}[data-theme=dark] .pomas-settings-panel,[data-theme=dark] .pomas-settings-panel header>button,[data-theme=dark] .pomas-segment,[data-theme=dark] .pomas-key,[data-theme=dark] .pomas-connection-form input{background:var(--d-surface-2);color:var(--c-lavender);border-color:var(--d-line)}[data-theme=dark] .pomas-settings-panel header,[data-theme=dark] .pomas-settings-panel>section>h3,[data-theme=dark] .pomas-settings-panel footer{border-color:var(--d-line)}[data-theme=dark] .pomas-settings-panel h2,[data-theme=dark] .pomas-settings-panel>section>h3,[data-theme=dark] .pomas-setting-row strong{color:var(--d-title)}[data-theme=dark] .pomas-setting-row{border-color:var(--d-line);background:var(--d-hover)}@media(max-width:600px){.pomas-settings-panel{width:100%;padding:22px 18px}.pomas-setting-row{flex-wrap:wrap}.pomas-setting-row>div:first-child{flex:1 1 100%}.pomas-segment{width:100%}.pomas-segment button{flex:1}.pomas-settings-panel footer{position:sticky;bottom:-22px;margin:20px -18px 0;padding:12px 18px;background:var(--bg)}.pomas-settings-panel footer button{width:100%}}
</style>

<style scoped>
.pomas-switch{position:relative;display:flex;align-items:center;height:24px}.pomas-switch span{position:relative}.pomas-switch span:after{position:absolute;top:50%;left:3px;margin:0;transform:translateY(-50%)}.pomas-switch input:checked+span:after{transform:translate(19px,-50%)}.pomas-settings-panel header>button{display:grid;place-items:center;line-height:1;padding:0;transform:translateY(-1px)}.pomas-settings-panel header>button:hover{border-color:var(--c-violet);background:var(--c-lavender)}.pomas-connection-actions{display:grid;grid-template-columns:1fr 1fr;gap:9px}.pomas-connection-actions button{display:flex;align-items:center;justify-content:flex-start;min-height:52px;padding:10px 11px;border:1px solid var(--line);border-radius:11px;background:var(--bg);color:var(--text-2);font-size:11px;font-weight:800;text-align:left}.pomas-connection-actions button::before{width:16px;height:16px;flex:0 0 auto;margin-right:8px;border:2px solid var(--c-violet);border-radius:50%;background:var(--bg);content:""}.pomas-connection-actions button:hover{border-color:var(--c-violet);background:var(--c-lavender)}.pomas-connection-actions button:hover::before{box-shadow:inset 0 0 0 3px var(--c-violet)}.pomas-connection-form{margin-top:12px;padding:15px;border:1px solid var(--line);border-radius:12px;background:var(--bg)}.pomas-connection-form::before{display:block;margin-bottom:2px;color:var(--c-violet);font-size:10px;font-weight:850;letter-spacing:.08em;text-transform:uppercase;content:"Existing organization details"}[data-theme=dark] .pomas-connection-actions button,[data-theme=dark] .pomas-connection-form{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .pomas-connection-actions button:hover{background:var(--d-hover)}@media(max-width:600px){.pomas-connection-actions{grid-template-columns:1fr}}
</style>

<style scoped>
.pomas-org-filter{display:grid;gap:2px;padding:6px;border:1px solid var(--line);border-radius:11px;background:var(--bg)}.pomas-org-filter .filter-option{font-size:11px}.pomas-org-filter .filter-option small{max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}[data-theme=dark] .pomas-org-filter{border-color:var(--d-line);background:var(--d-surface-2)}
</style>

<style scoped>
.pomas-update-connection{width:max-content;min-height:38px;padding:0 13px;border:1px solid var(--c-violet);border-radius:9px;background:var(--c-violet);color:white;font-size:11px;font-weight:850;cursor:pointer}.pomas-update-connection:hover{filter:brightness(1.08)}[data-theme=dark] .pomas-update-connection{border-color:var(--c-orchid);background:var(--c-orchid);color:var(--c-ink)}
</style>

<style scoped>
.pomas-setting-row--stack:has(.pomas-update-connection){display:flex;align-items:center}.pomas-setting-row--stack:has(.pomas-update-connection)>div:first-child{min-width:0;flex:1}.pomas-update-connection{margin-left:auto;border-color:#3f8f28;background:#3f8f28}.pomas-update-connection:hover{border-color:#58a939;background:#58a939;filter:none}.pomas-settings-panel .drawer-primary,.pomas-settings-panel .drawer-secondary{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:0 15px;border-radius:9px;font-size:12px;font-weight:850;line-height:1;cursor:pointer}.pomas-settings-panel .drawer-primary{border:1px solid var(--c-violet);background:var(--c-violet);color:white}.pomas-settings-panel .drawer-primary:hover{filter:brightness(1.08)}.pomas-settings-panel .drawer-secondary{border:1px solid var(--line);background:var(--bg);color:var(--text-2)}.pomas-settings-panel .drawer-secondary:hover{border-color:var(--c-violet);background:var(--c-lavender);color:var(--c-violet)}.pomas-settings-panel footer .drawer-secondary{min-width:86px}.pomas-settings-panel header>button{align-content:center;padding-bottom:2px}[data-theme=dark] .pomas-settings-panel .drawer-secondary{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .pomas-settings-panel .drawer-secondary:hover{border-color:var(--c-orchid);background:var(--d-hover);color:var(--c-orchid)}[data-theme=dark] .pomas-update-connection{border-color:#5db747;background:#5db747;color:#102008}
</style>

<style scoped>
.pomas-settings-panel .project-team-actions{display:flex;align-items:center;gap:9px;flex-wrap:nowrap;width:100%}.pomas-settings-panel .project-team-actions .drawer-primary{margin-left:auto;white-space:nowrap}.pomas-settings-panel .project-team-actions .drawer-secondary{white-space:nowrap}.pomas-settings-panel .drawer-secondary{background:white}.pomas-settings-panel footer .drawer-secondary{background:white}[data-theme=dark] .pomas-settings-panel .drawer-secondary,[data-theme=dark] .pomas-settings-panel footer .drawer-secondary{background:var(--d-surface-2)}@media(max-width:600px){.pomas-settings-panel .project-team-actions{flex-wrap:wrap}.pomas-settings-panel .project-team-actions .drawer-primary{margin-left:0;flex:1}.pomas-settings-panel .project-team-actions .drawer-secondary{flex:1}}
</style>

<style scoped>
.pomas-setting-row--stack:has(.pomas-connection-form){flex-wrap:wrap}.pomas-setting-row--stack:has(.pomas-connection-form)>.pomas-connection-form{flex:0 0 100%;width:100%}.pomas-setting-row--stack:has(.pomas-connection-form)>.project-action-error,.pomas-setting-row--stack:has(.pomas-connection-form)>.settings-success{flex:0 0 100%}
</style>
