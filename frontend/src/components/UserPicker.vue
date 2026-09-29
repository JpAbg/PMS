<template>
  <section ref="root" class="user-picker">
    <div class="user-picker-head"><span>{{ label }}</span><button type="button" class="add-user" :aria-expanded="open" @click="open = !open">+ Add user</button></div>
    <p v-if="!modelValue.length" class="user-empty">No users added yet.</p>
    <div v-else class="user-chips"><span v-for="user in selectedUsers" :key="user.name" class="user-chip"><i>{{ initials(user.full_name || user.name) }}</i><b>{{ user.full_name || user.name }}</b><button v-if="!props.lockedUsers.includes(user.name)" type="button" :aria-label="`Remove ${user.full_name || user.name}`" @click="remove(user.name)"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M10 11v6m4-6v6M9 7l1-2h4l1 2m-8 0 1 13h8l1-13"/></svg></button></span></div>
    <div v-if="open" class="user-popover" role="dialog" aria-label="Add user">
      <p>Select a user</p>
      <button v-for="user in availableUsers" :key="user.name" type="button" class="user-option" @click="add(user.name)"><i>{{ initials(user.full_name || user.name) }}</i><span><b>{{ user.full_name || user.name }}</b><small>{{ user.name }}</small></span><em>Add</em></button>
      <div v-if="!availableUsers.length" class="user-picker-empty">Everyone available is already added.</div>
    </div>
    <small v-if="help">{{ help }}</small>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import type { TaskFormMember } from "../services/api"
const props = withDefaults(defineProps<{ modelValue: string[]; users: TaskFormMember[]; label: string; help?: string; lockedUsers?: string[] }>(), { lockedUsers: () => [] })
const emit = defineEmits<{ "update:modelValue": [users: string[]] }>()
const root = ref<HTMLElement | null>(null)
const open = ref(false)
const selectedUsers = computed(() => props.modelValue.map((name) => props.users.find((user) => user.name === name) || { name, full_name: name }))
const availableUsers = computed(() => props.users.filter((user) => !props.modelValue.includes(user.name)))
function add(name: string) { if (!props.modelValue.includes(name)) emit("update:modelValue", [...props.modelValue, name]); open.value = false }
function remove(name: string) { emit("update:modelValue", props.modelValue.filter((user) => user !== name)) }
function initials(value: string) { return value.split(/[@.\s]+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("") }
function outside(event: MouseEvent) { if (root.value && !root.value.contains(event.target as Node)) open.value = false }
onMounted(() => document.addEventListener("click", outside))
onBeforeUnmount(() => document.removeEventListener("click", outside))
</script>

<style scoped>
.user-picker{position:relative;display:grid;gap:9px}.user-picker-head{display:flex;align-items:center;justify-content:space-between;gap:12px;color:var(--text-2);font-size:11px;font-weight:800}.add-user{min-height:32px;padding:0 10px;border:1px solid var(--c-violet);border-radius:8px;background:transparent;color:var(--c-violet);font-size:10px;font-weight:850;cursor:pointer}.add-user:hover{background:var(--c-lavender)}.user-empty{margin:0;padding:13px;border:1px dashed var(--line);border-radius:10px;color:var(--muted);font-size:11px;text-align:center}.user-chips{display:flex;flex-wrap:wrap;gap:7px}.user-chip{display:flex;align-items:center;gap:7px;min-height:34px;padding:4px 5px 4px 6px;border:1px solid var(--line);border-radius:9px;background:var(--line-soft);color:var(--text-2);font-size:10px}.user-chip i,.user-option i{display:grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--c-lavender);color:var(--c-plum);font-size:7px;font-style:normal;font-weight:850}.user-chip button{display:grid;place-items:center;width:22px;height:22px;padding:0;border:0;border-radius:6px;background:transparent;color:#b83f4a;cursor:pointer}.user-chip button svg{width:13px;height:13px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.user-chip button:hover{background:#ffe7e9}.user-popover{position:absolute;z-index:20;top:39px;right:0;left:0;display:grid;gap:5px;max-height:250px;padding:10px;overflow:auto;border:1px solid var(--line);border-radius:11px;background:var(--c-lavender);box-shadow:0 16px 34px rgba(12,9,20,.16)}.user-popover>p{margin:2px 4px 6px;color:var(--faint);font-size:9px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}.user-option{display:flex;align-items:center;gap:9px;width:100%;padding:8px;border:0;border-radius:8px;background:transparent;color:var(--text-2);text-align:left;cursor:pointer}.user-option:hover{background:var(--c-lavender)}.user-option span{display:grid;gap:2px;min-width:0}.user-option b{overflow:hidden;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.user-option small{overflow:hidden;color:var(--faint);font-size:9px;text-overflow:ellipsis;white-space:nowrap}.user-option em{margin-left:auto;color:var(--c-violet);font-size:9px;font-style:normal;font-weight:850}.user-picker>small{color:var(--faint);font-size:9px;font-weight:600;line-height:1.4}[data-theme=dark] .user-empty,[data-theme=dark] .user-chip,[data-theme=dark] .user-popover{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .user-option{color:var(--c-lavender)}[data-theme=dark] .user-option:hover,[data-theme=dark] .add-user:hover{background:var(--d-hover)}
</style>
