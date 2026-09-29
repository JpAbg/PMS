<template>
  <main class="auth-page">
    <section class="auth-story">
      <a class="brand auth-brand" href="/pms">
        <span class="brand-mark"><img src="/Pomas-Logo.png" alt="" /></span>
        <div><strong>Pomas</strong><small>Project workspace</small></div>
      </a>
      <div class="auth-message">
        <p class="eyebrow">Plan together. Move faster.</p>
        <h1>Every project, clearly in motion.</h1>
        <p>Turn ERPNext projects into focused boards your whole team can understand on desktop and mobile.</p>
      </div>
      <div class="auth-preview" aria-hidden="true">
        <div class="preview-toolbar">
          <span>Project boards</span>
          <b>Live preview</b>
        </div>
        <article class="preview-project">
          <div class="preview-card-copy">
            <span class="preview-status status-progress">In progress</span>
            <strong>Product launch</strong>
          </div>
          <div class="preview-meta">
            <span class="preview-avatars"><i>AM</i><i>JL</i><i>+2</i></span>
            <b>8 tasks</b>
          </div>
        </article>
        <article class="preview-project">
          <div class="preview-card-copy">
            <span class="preview-status status-review">Review</span>
            <strong>Mobile app</strong>
          </div>
          <div class="preview-meta">
            <span class="preview-avatars"><i>JP</i><i>SK</i></span>
            <b>5 tasks</b>
          </div>
        </article>
        <article class="preview-project">
          <div class="preview-card-copy">
            <span class="preview-status status-done">Done</span>
            <strong>Client onboarding</strong>
          </div>
          <div class="preview-meta">
            <span class="preview-avatars"><i>NB</i><i>RA</i><i>+3</i></span>
            <b>12 tasks</b>
          </div>
        </article>
      </div>
    </section>

    <section class="auth-panel">
      <button class="theme-toggle auth-theme-toggle" :aria-label="`Use ${theme === 'light' ? 'dark' : 'light'} theme`" @click="toggleTheme">
        {{ theme === "light" ? "☾" : "☀" }}
      </button>
      <form class="auth-form" @submit.prevent="login">
        <p class="eyebrow">Welcome back</p>
        <h2>Sign in to Pomas</h2>
        <p class="form-intro">Use your workspace account to continue.</p>

        <label>
          <span>Email</span>
          <span class="input-shell">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <rect x="3" y="5" width="18" height="14" rx="2" />
              <path d="m4 7 8 6 8-6" />
            </svg>
            <input v-model.trim="email" type="email" autocomplete="username" placeholder="you@example.com" required />
          </span>
        </label>
        <label>
          <span class="field-heading">
            <span>Password</span>
            <a class="forgot-link" href="/login#forgot">Forgot password?</a>
          </span>
          <span class="input-shell">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <rect x="5" y="10" width="14" height="10" rx="2" />
              <path d="M8 10V7a4 4 0 0 1 8 0v3" />
            </svg>
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              placeholder="Enter your password"
              required
            />
            <button
              class="password-toggle"
              type="button"
              :aria-label="showPassword ? 'Hide password' : 'Show password'"
              :title="showPassword ? 'Hide password' : 'Show password'"
              @click="showPassword = !showPassword"
            >
              <svg v-if="showPassword" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 3l18 18M10.6 10.7a2 2 0 0 0 2.7 2.7M9.9 4.2A10.8 10.8 0 0 1 12 4c5.2 0 9 5.2 9 5.2a17 17 0 0 1-3.1 3.7M6.6 6.6A16.4 16.4 0 0 0 3 9.2S6.8 14.4 12 14.4c.7 0 1.4-.1 2-.3" />
              </svg>
              <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 12s3.8-5.2 9-5.2 9 5.2 9 5.2-3.8 5.2-9 5.2S3 12 3 12Z" />
                <circle cx="12" cy="12" r="2.4" />
              </svg>
            </button>
          </span>
        </label>

        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="primary-button auth-submit" :disabled="submitting">
          {{ submitting ? "Signing in…" : "Sign in" }}
        </button>
      </form>

      <div class="signup-prompt">
        <span>New to Pomas?</span>
        <RouterLink class="signup-action" to="/signup">Create an account</RouterLink>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { callPms } from "../services/api"
import { theme, toggleTheme } from "../services/theme"

const email = ref("")
const password = ref("")
const showPassword = ref(false)
const submitting = ref(false)
const error = ref("")

async function login() {
  submitting.value = true
  error.value = ""
  try {
    await callPms("login", { usr: email.value, pwd: password.value })
    window.location.assign("/pms")
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Incorrect email or password."
  } finally {
    submitting.value = false
  }
}
</script>
