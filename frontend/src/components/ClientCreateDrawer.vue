<template>
  <Teleport to="body">
    <Transition name="client-drawer">
      <div class="client-drawer" role="dialog" aria-modal="true" aria-labelledby="client-drawer-title">
        <button class="client-backdrop" type="button" aria-label="Close client creation" @click="close" />
        <section class="client-panel">
          <header><div><p>New client</p><h2 id="client-drawer-title">Client details</h2><span>Create the client record used by this project.</span></div><button type="button" aria-label="Close" @click="close">×</button></header>
          <form @submit.prevent="save">
            <label class="client-type-select"><span>Client type <b>*</b></span><PomasSelect v-model="form.customer_type" label="Client type" :options="typeOptions" /></label>
            <label><span>{{ form.customer_type === 'Individual' ? 'Full name' : 'Organization name' }} <b>*</b></span><input ref="nameInput" v-model.trim="form.customer_name" maxlength="140" required placeholder="Client name" /></label>
            <div class="client-grid"><label><span>Email</span><input v-model.trim="form.email" type="email" placeholder="client@example.com" /></label><label><span>Phone</span><input v-model.trim="form.phone" type="tel" placeholder="+961 …" /></label></div>
            <section class="address-section"><p>Address <em>Optional</em></p><label><span>Address line 1</span><input v-model.trim="form.address_line1" placeholder="Building, street" /></label><label><span>Address line 2</span><input v-model.trim="form.address_line2" placeholder="Suite, floor, district" /></label><div class="client-grid"><label><span>City</span><input v-model.trim="form.city" placeholder="Beirut" /></label><label><span>Country</span><input v-model.trim="form.country" placeholder="Lebanon" /></label></div><small>If you add an address, line 1, city, and country are required.</small></section>
            <p v-if="error" class="client-error" role="alert">{{ error }}</p>
            <footer><button class="drawer-secondary" type="button" :disabled="saving" @click="close">Cancel</button><button class="drawer-primary" type="submit" :disabled="saving">{{ saving ? 'Creating…' : 'Create client' }}</button></footer>
          </form>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from "vue"
import PomasSelect from "./PomasSelect.vue"
import { callPms } from "../services/api"
const emit = defineEmits<{ close: []; created: [client: { name: string; customer_name: string }] }>()
const nameInput = ref<HTMLInputElement | null>(null)
const saving = ref(false)
const error = ref("")
const form = reactive({ customer_type: "Organization", customer_name: "", email: "", phone: "", address_line1: "", address_line2: "", city: "", country: "" })
const typeOptions = [{ value: "Organization", label: "Organization" }, { value: "Individual", label: "Individual" }]
onMounted(() => void nextTick(() => nameInput.value?.focus()))
function close() { if (!saving.value) emit("close") }
async function save() { error.value = ""; if (!form.customer_name) { error.value = "Enter the client name."; nameInput.value?.focus(); return } saving.value = true; try { emit("created", await callPms("pms.api.create_client", form)) } catch (reason) { error.value = reason instanceof Error ? reason.message : "Unable to create this client." } finally { saving.value = false } }
</script>

<style scoped>
.client-drawer{position:fixed;inset:0;z-index:650;display:flex;justify-content:flex-end}.client-backdrop{position:absolute;inset:0;border:0;background:rgba(12,9,20,.55);backdrop-filter:blur(3px)}.client-panel{position:relative;z-index:1;width:min(540px,100%);height:100%;overflow:auto;padding:28px;background:var(--bg);color:var(--text-2);box-shadow:-18px 0 48px rgba(0,0,0,.26);scrollbar-width:thin;scrollbar-color:transparent transparent}.client-panel:hover,.client-panel:focus-within{scrollbar-color:color-mix(in srgb,var(--c-orchid) 62%,transparent) transparent}.client-panel::-webkit-scrollbar{width:10px}.client-panel::-webkit-scrollbar-track{background:transparent}.client-panel::-webkit-scrollbar-thumb{border:3px solid transparent;border-radius:999px;background:transparent;background-clip:padding-box}.client-panel:hover::-webkit-scrollbar-thumb{background:color-mix(in srgb,var(--c-orchid) 62%,transparent);background-clip:padding-box}header{display:flex;justify-content:space-between;gap:18px;padding-bottom:20px;border-bottom:1px solid var(--line)}header p{margin:0;color:var(--c-violet);font-size:10px;font-weight:850;letter-spacing:.1em;text-transform:uppercase}h2{margin:6px 0;color:var(--c-ink);font-size:25px;letter-spacing:-.035em}header span{color:var(--muted);font-size:12px}header>button{width:36px;height:36px;border:1px solid var(--line);border-radius:10px;background:white;color:var(--text-2);font-size:22px;cursor:pointer}form{display:grid;gap:17px;margin-top:23px}label{display:grid;gap:7px;color:var(--text-2);font-size:11px;font-weight:800}label span{display:flex}label b{color:#d14f5a}input{width:100%;min-height:43px;padding:10px 12px;border:1px solid var(--line);border-radius:9px;background:white;color:var(--c-ink);outline:none}input:focus{border-color:var(--c-violet);box-shadow:0 0 0 3px color-mix(in srgb,var(--c-violet) 16%,transparent)}.client-grid{display:grid;grid-template-columns:1fr 1fr;gap:13px}.address-section{display:grid;gap:12px;padding:15px;border:1px solid var(--line);border-radius:12px;background:var(--line-soft)}.address-section p{margin:0;color:var(--text-2);font-size:11px;font-weight:850}.address-section em{margin-left:6px;color:var(--faint);font-size:9px;font-style:normal;text-transform:uppercase}.address-section small{color:var(--muted);font-size:9px}.client-error{margin:0;padding:10px 11px;border:1px solid #ffd2d6;border-radius:9px;background:#fff0f1;color:#b83f4a;font-size:11px}footer{display:flex;justify-content:flex-end;gap:9px;padding-top:17px;border-top:1px solid var(--line)}.drawer-primary,.drawer-secondary{min-height:40px;padding:0 15px;border-radius:9px;font-size:12px;font-weight:800;cursor:pointer}.drawer-primary{border:1px solid var(--c-violet);background:var(--c-violet);color:white}.drawer-secondary{border:1px solid var(--line);background:white;color:var(--text-2)}.client-drawer-enter-active,.client-drawer-leave-active{transition:opacity .18s}.client-drawer-enter-active .client-panel,.client-drawer-leave-active .client-panel{transition:transform .2s}.client-drawer-enter-from,.client-drawer-leave-to{opacity:0}.client-drawer-enter-from .client-panel,.client-drawer-leave-to .client-panel{transform:translateX(28px)}[data-theme=dark] .client-panel{background:var(--c-ink);color:var(--c-lavender)}[data-theme=dark] .client-panel:hover,[data-theme=dark] .client-panel:focus-within{scrollbar-color:rgba(88,247,7,.62) transparent}[data-theme=dark] .client-panel:hover::-webkit-scrollbar-thumb{background:rgba(88,247,7,.62);background-clip:padding-box}[data-theme=dark] h2{color:var(--d-title)}[data-theme=dark] header,[data-theme=dark] footer{border-color:var(--d-line)}[data-theme=dark] header>button,[data-theme=dark] input,[data-theme=dark] .drawer-secondary{border-color:var(--d-line);background:var(--d-surface-2);color:var(--c-lavender)}[data-theme=dark] .address-section{border-color:var(--d-line);background:var(--d-hover);color:var(--c-lavender)}[data-theme=dark] .client-error{border-color:#5c2631;background:#35181f;color:#ffb8c0}@media(max-width:600px){.client-panel{padding:22px 18px}.client-grid{grid-template-columns:1fr}footer{flex-direction:column-reverse}footer button{width:100%}}
</style>
