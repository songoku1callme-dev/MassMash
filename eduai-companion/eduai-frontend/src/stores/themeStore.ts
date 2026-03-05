import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'dark' | 'light' | 'system'

interface ThemeStore {
  theme: Theme
  setTheme: (theme: Theme) => void
  resolvedTheme: 'dark' | 'light'
}

function getSystemTheme(): 'dark' | 'light' {
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function resolveTheme(theme: Theme): 'dark' | 'light' {
  return theme === 'system' ? getSystemTheme() : theme
}

function applyTheme(resolved: 'dark' | 'light') {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-theme', resolved)
  // Keep Tailwind dark: variants working
  document.documentElement.classList.toggle('dark', resolved === 'dark')
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => {
      const initialTheme: Theme = 'system'
      const initialResolved = resolveTheme(initialTheme)
      applyTheme(initialResolved)

      return {
        theme: initialTheme,
        resolvedTheme: initialResolved,
        setTheme: (theme) => {
          const resolved = resolveTheme(theme)
          set({ theme, resolvedTheme: resolved })
          applyTheme(resolved)
        },
      }
    },
    {
      name: 'lumnos-theme',
      onRehydrateStorage: () => (state) => {
        if (!state) return
        const resolved = resolveTheme(state.theme)
        useThemeStore.setState({ resolvedTheme: resolved })
        applyTheme(resolved)
      },
    }
  )
)

// Listen for system theme changes
if (typeof window !== 'undefined') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    const store = useThemeStore.getState()
    if (store.theme !== 'system') return

    const resolved = e.matches ? 'dark' : 'light'
    useThemeStore.setState({ resolvedTheme: resolved })
    applyTheme(resolved)
  })
}

export type { Theme, ThemeStore }
