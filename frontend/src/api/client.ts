export class ApiError extends Error {
  codigo?: string
  status: number

  constructor(message: string, status = 400, codigo?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.codigo = codigo
  }
}

export function getCsrfToken(): string {
  if (typeof document === 'undefined') return ''
  const cookies = document.cookie.split(';')
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=')
    if (name === 'csrftoken') {
      return decodeURIComponent(value)
    }
  }
  return ''
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : endpoint

  const headers = new Headers(options.headers || {})

  // Configurações padrão
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json')
  }

  // Define CSRF para métodos não-GET
  const method = (options.method || 'GET').toUpperCase()
  if (method !== 'GET' && method !== 'HEAD') {
    const token = getCsrfToken()
    if (token) {
      headers.set('X-CSRFToken', token)
    }
    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json')
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // Envia cookies de sessão da mesma origem
  })

  // Se redirecionado para página HTML de login (sessão expirada)
  if (response.redirected && response.url.includes('/accounts/login/')) {
    window.location.href = response.url
    throw new ApiError('Sessão expirada. Redirecionando para login...', 401, 'NAO_AUTENTICADO')
  }

  const contentType = response.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      if (contentType.includes('text/html')) {
        window.location.href = `/accounts/login/?next=${encodeURIComponent(window.location.pathname)}`
      }
    }

    if (isJson) {
      const errData = await response.json()
      throw new ApiError(
        errData.erro || errData.mensagem || 'Erro na requisição ao servidor.',
        response.status,
        errData.codigo
      )
    }

    const text = await response.text()
    throw new ApiError(text || `Erro HTTP ${response.status}`, response.status)
  }

  if (isJson) {
    const data = await response.json()
    if (data && typeof data === 'object' && 'ok' in data && !data.ok) {
      throw new ApiError(data.erro || 'Operação falhou.', 400, data.codigo)
    }
    return data as T
  }

  return (await response.text()) as unknown as T
}

export const api = {
  get: <T = any>(endpoint: string, options?: RequestInit) =>
    apiRequest<T>(endpoint, { ...options, method: 'GET' }),

  post: <T = any>(endpoint: string, body?: any, options?: RequestInit) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  put: <T = any>(endpoint: string, body?: any, options?: RequestInit) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  patch: <T = any>(endpoint: string, body?: any, options?: RequestInit) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  delete: <T = any>(endpoint: string, options?: RequestInit) =>
    apiRequest<T>(endpoint, { ...options, method: 'DELETE' }),
}
