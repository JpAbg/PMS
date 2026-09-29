<template>
  <main class="auth-page">
    <section class="auth-story signup-story">
      <a class="brand auth-brand" href="/pms"><span class="brand-mark"><img src="/Pomas-Logo.png" alt="" /></span><div><strong>Pomas</strong><small>Project workspace</small></div></a>
      <div class="auth-message">
        <p class="eyebrow">Start with a clear board.</p>
        <h1>Bring your work into motion.</h1>
        <p>Create your Pomas account, then join the projects your team shares with you.</p>
        <section class="signup-offers" aria-label="What Pomas offers">
          <p>What Pomas offers</p>
          <ul>
            <li><strong>Clear boards</strong><span>See the work that moves each project forward.</span></li>
            <li><strong>Shared ownership</strong><span>Keep tasks, members, and due dates in one place.</span></li>
            <li><strong>Work anywhere</strong><span>Stay connected on desktop and mobile.</span></li>
          </ul>
        </section>
      </div>
    </section>
    <section class="auth-panel">
      <button class="theme-toggle auth-theme-toggle" :aria-label="`Use ${theme === 'light' ? 'dark' : 'light'} theme`" @click="toggleTheme">{{ theme === 'light' ? '☾' : '☀' }}</button>
      <form class="auth-form signup-form" @submit.prevent="signup">
        <p class="eyebrow">Create your account</p><h2>Welcome to Pomas</h2><p class="form-intro">Use a work email and a secure password to get started.</p>
        <label><span>Full name</span><span class="input-shell"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M4.5 20c.8-4 3.2-6 7.5-6s6.7 2 7.5 6"/></svg><input v-model.trim="fullName" autocomplete="name" placeholder="Your name" required /></span></label>
        <label><span>Email</span><span class="input-shell"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/></svg><input v-model.trim="email" type="email" autocomplete="email" placeholder="you@example.com" required /></span></label>
        <label><span>Password</span><span class="input-shell"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg><input v-model="password" :type="showPassword ? 'text' : 'password'" autocomplete="new-password" placeholder="At least 10 characters" minlength="10" required /><button class="password-toggle" type="button" :aria-label="showPassword ? 'Hide password' : 'Show password'" @click="showPassword = !showPassword"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12s3.8-5.2 9-5.2 9 5.2 9 5.2-3.8 5.2-9 5.2S3 12 3 12Z"/><circle cx="12" cy="12" r="2.4"/></svg></button></span></label>
        <label><span>Confirm password</span><span class="input-shell"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg><input v-model="confirmation" :type="showPassword ? 'text' : 'password'" autocomplete="new-password" placeholder="Repeat your password" minlength="10" required /></span></label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p><button class="primary-button auth-submit" :disabled="submitting">{{ submitting ? 'Creating account…' : 'Create account' }}</button>
      </form>
      <section v-if="socialProviders.length" class="social-auth" aria-label="Social sign-up">
        <p class="social-divider"><span>or continue with</span></p>
        <div class="social-buttons">
          <a v-for="provider in socialProviders" :key="provider.provider" class="social-button" :class="`social-button--${provider.provider}`" :href="provider.url"><span class="social-provider-icon" aria-hidden="true">{{ provider.provider === 'google' ? 'G' : '⌘' }}</span>Continue with {{ provider.label }}</a>
        </div>
      </section>
      <div class="signup-prompt"><span>Already have an account?</span><RouterLink class="signup-action" to="/login">Sign in</RouterLink></div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { callPms } from '../services/api'
import { theme, toggleTheme } from '../services/theme'
const fullName = ref(''); const email = ref(''); const password = ref(''); const confirmation = ref(''); const showPassword = ref(false); const submitting = ref(false); const error = ref(''); const socialProviders = ref<{ provider: string; label: string; url: string }[]>([])
onMounted(async () => { try { socialProviders.value = await callPms<{ provider: string; label: string; url: string }[]>('pms.api.get_social_login_options') } catch { socialProviders.value = [] } })
async function signup() { error.value = ''; if (password.value !== confirmation.value) { error.value = 'The passwords do not match.'; return }; submitting.value = true; try { await callPms('pms.api.signup', { full_name: fullName.value, email: email.value, password: password.value }); await callPms('login', { usr: email.value, pwd: password.value }); window.location.assign('/pms') } catch (reason) { error.value = reason instanceof Error ? reason.message : 'Unable to create your account.' } finally { submitting.value = false } }
</script>
