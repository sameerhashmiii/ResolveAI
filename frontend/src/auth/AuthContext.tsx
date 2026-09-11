import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'

import {
  demoLogin as requestDemoLogin,
  getCurrentUser,
  login as requestLogin,
  logout as requestLogout,
} from '../api/auth'
import { ApiError } from '../api/client'
import type { User } from '../api/types'

interface AuthValue {
  user: User | null
  csrfToken: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  demoLogin: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [csrfToken, setCsrfToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    void getCurrentUser(controller.signal)
      .then((response) => {
        if (!active) return
        setUser(response.user)
        setCsrfToken(response.csrf_token)
      })
      .catch((error: unknown) => {
        if (!active) return
        if (!(error instanceof ApiError && error.status === 401)) {
          console.error('Authentication bootstrap failed', error)
        }
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
      controller.abort()
    }
  }, [])

  const acceptSession = (
    response: Awaited<ReturnType<typeof requestLogin>>,
  ) => {
    setUser(response.user)
    setCsrfToken(response.csrf_token)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        csrfToken,
        isLoading,
        login: async (email, password) => {
          acceptSession(await requestLogin(email, password))
        },
        demoLogin: async () => {
          acceptSession(await requestDemoLogin())
        },
        logout: async () => {
          try {
            if (csrfToken) await requestLogout(csrfToken)
          } finally {
            setUser(null)
            setCsrfToken(null)
          }
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used within AuthProvider')
  return value
}
