<template>
  <div ref="root" class="pomas-select">
    <button class="select-trigger" type="button" :aria-expanded="open" @click="open = !open"><span>{{ selectedLabel }}</span><svg class="select-chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4" /></svg></button>
    <Transition name="select-menu">
      <div v-if="open" class="select-menu" role="listbox" :aria-label="label">
        <button v-for="option in options" :key="option.value" type="button" :class="{ selected: option.value === modelValue }" role="option" :aria-selected="option.value === modelValue" @click="choose(option.value)">{{ option.label }}</button>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
type SelectOption = { value: string; label: string }
const props = defineProps<{ modelValue: string; options: SelectOption[]; label: string }>()
const emit = defineEmits<{ "update:modelValue": [value: string] }>()
const root = ref<HTMLElement | null>(null)
const open = ref(false)
const selectedLabel = computed(() => props.options.find((option) => option.value === props.modelValue)?.label || props.modelValue)
function choose(value: string) { emit("update:modelValue", value); open.value = false }
function outside(event: MouseEvent) { if (root.value && !root.value.contains(event.target as Node)) open.value = false }
function keydown(event: KeyboardEvent) { if (event.key === "Escape") open.value = false }
onMounted(() => { document.addEventListener("click", outside); document.addEventListener("keydown", keydown) })
onBeforeUnmount(() => { document.removeEventListener("click", outside); document.removeEventListener("keydown", keydown) })
</script>

<style scoped>
.pomas-select{position:relative;min-width:0}.select-trigger{display:flex;align-items:center;justify-content:space-between;gap:15px;width:100%;min-height:43px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:color-mix(in srgb,var(--c-lavender) 20%,white);color:var(--text-2);font-size:12px;font-weight:800;text-align:left;cursor:pointer;transition:border-color .15s,box-shadow .15s,background .15s}.select-trigger:hover,.select-trigger:focus-visible{border-color:var(--c-violet);box-shadow:0 0 0 3px color-mix(in srgb,var(--c-violet) 13%,transparent);outline:none}.select-chevron{display:block;flex:0 0 16px;width:16px;height:16px;margin-left:auto;fill:none;stroke:var(--c-violet);stroke-width:2;stroke-linecap:round;stroke-linejoin:round;transform:rotate(0deg);transform-box:fill-box;transform-origin:50% 50%;transition:transform .16s;will-change:transform}.select-trigger[aria-expanded=true] .select-chevron{transform:rotate(-180deg)}.select-menu{position:absolute;z-index:40;top:calc(100% + 8px);left:0;width:100%;min-width:170px;padding:7px;border:1px solid color-mix(in srgb,var(--c-violet) 34%,var(--line));border-radius:13px;background:color-mix(in srgb,var(--bg) 96%,white);box-shadow:0 18px 36px rgba(12,9,20,.15)}.select-menu button{display:block;width:100%;min-height:38px;padding:0 10px;border:0;border-radius:8px;background:transparent;color:var(--text-2);font-size:12px;font-weight:750;text-align:left;cursor:pointer}.select-menu button:hover,.select-menu button.selected{background:var(--c-lavender);color:var(--c-plum)}.select-menu button.selected::after{float:right;color:var(--c-violet);content:"✓"}[data-theme=dark] .select-trigger{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .select-menu{border-color:var(--d-line);background:var(--d-surface)}[data-theme=dark] .select-menu button{color:var(--c-lavender)}[data-theme=dark] .select-menu button:hover,[data-theme=dark] .select-menu button.selected{background:var(--d-hover);color:white}.select-menu-enter-active,.select-menu-leave-active{transition:opacity .12s,transform .12s}.select-menu-enter-from,.select-menu-leave-to{opacity:0;transform:translateY(-4px)}
</style>
