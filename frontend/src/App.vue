<template>
  <RouterView />
</template>

<script setup lang="ts">
import { initTheme } from "./services/theme"

initTheme()
</script>
