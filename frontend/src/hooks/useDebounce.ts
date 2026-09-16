import { useState, useEffect } from 'react'

/**
 * Hook para adiar a atualização de um valor até que o usuário pare de digitar.
 * Ideal para campos de busca e filtros, evitando requisições HTTP desnecessárias.
 */
export function useDebounce<T>(value: T, delay: number = 350): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(timer)
    }
  }, [value, delay])

  return debouncedValue
}
