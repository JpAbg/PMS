import { ref } from "vue"

export type Theme = "light" | "dark"

export const theme = ref<Theme>("light")

export function initTheme() {
  const savedTheme = window.localStorage.getItem("pomas-theme") as Theme | null
  const preferredTheme: Theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
  setTheme(savedTheme === "light" || savedTheme === "dark" ? savedTheme : preferredTheme, false)
}

export function toggleTheme() {
  setTheme(theme.value === "light" ? "dark" : "light")
}

export function setTheme(value: Theme, persist = true) {
  theme.value = value
  document.documentElement.dataset.theme = value
  document.documentElement.style.colorScheme = value
  document.querySelector("meta[name=theme-color]")?.setAttribute("content", value === "dark" ? "#0b0710" : "#17111f")
  if (persist) window.localStorage.setItem("pomas-theme", value)
}
