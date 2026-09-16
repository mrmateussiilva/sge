import { useEffect, useState } from 'react'

export function usePreferences() {
  const [isDark, setIsDark] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    const saved = localStorage.getItem('sge_theme')
    if (saved) return saved === 'dark'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  const [ocultarValores, setOcultarValores] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return localStorage.getItem('sgeValoresOcultos') === 'true'
  })

  useEffect(() => {
    const root = document.documentElement
    if (isDark) {
      root.classList.add('dark')
      localStorage.setItem('sge_theme', 'dark')
    } else {
      root.classList.remove('dark')
      localStorage.setItem('sge_theme', 'light')
    }
  }, [isDark])

  useEffect(() => {
    const body = document.body
    if (ocultarValores) {
      body.classList.add('valores-ocultos')
      localStorage.setItem('sgeValoresOcultos', 'true')
    } else {
      body.classList.remove('valores-ocultos')
      localStorage.setItem('sgeValoresOcultos', 'false')
    }
  }, [ocultarValores])

  return {
    isDark,
    toggleTheme: () => setIsDark((prev) => !prev),
    ocultarValores,
    toggleOcultarValores: () => setOcultarValores((prev) => !prev),
  }
}
