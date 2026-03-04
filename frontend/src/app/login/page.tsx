"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { login } from "@/services/api/auth"

interface LoginFormState {
  username: string
  password: string
}

const initialFormState: LoginFormState = {
  username: "",
  password: "",
}

export default function LoginPage() {
  const router = useRouter()
  const [formData, setFormData] = useState<LoginFormState>(initialFormState)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFieldChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target
    setFormData((previousState) => ({
      ...previousState,
      [name]: value,
    }))
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    if (!formData.username.trim() || !formData.password) {
      setError("Preencha usuário e senha.")
      return
    }

    try {
      setIsSubmitting(true)
      await login({
        username: formData.username.trim(),
        password: formData.password,
      })

      router.push("/")
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Não foi possível autenticar"
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-slate-100 via-blue-100/70 to-indigo-200/50 p-6">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(37,99,235,0.24),_transparent_52%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,_rgba(30,64,175,0.20),_transparent_46%)]" />

      <Card className="relative w-full max-w-md border-blue-200/80 bg-white/92 shadow-2xl backdrop-blur-sm">
        <CardHeader className="space-y-2 text-center">
          <CardTitle className="text-2xl">Entrar</CardTitle>
          <p className="text-sm text-muted-foreground">Acesse o painel de gestão de contratos.</p>
        </CardHeader>

        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <label className="space-y-2">
              <span className="text-sm font-medium">Usuário</span>
              <input
                required
                name="username"
                value={formData.username}
                onChange={handleFieldChange}
                className="h-10 w-full rounded-md border border-blue-200 bg-white px-3 text-sm outline-none ring-0 transition-shadow focus-visible:ring-2 focus-visible:ring-blue-300"
                placeholder="Seu usuário"
                autoComplete="username"
              />
            </label>

            <label className="space-y-2">
              <span className="text-sm font-medium">Senha</span>
              <input
                required
                type="password"
                name="password"
                value={formData.password}
                onChange={handleFieldChange}
                className="h-10 w-full rounded-md border border-blue-200 bg-white px-3 text-sm outline-none ring-0 transition-shadow focus-visible:ring-2 focus-visible:ring-blue-300"
                placeholder="Sua senha"
                autoComplete="current-password"
              />
            </label>

            {error ? (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            ) : null}

            <Button type="submit" className="w-full shadow-lg" disabled={isSubmitting}>
              {isSubmitting ? "Entrando..." : "Entrar"}
            </Button>
          </form>

          <p className="mt-4 text-center text-xs text-muted-foreground">
            Problemas para acessar?{" "}
            <Link href="/api/docs" className="underline">
              Ver documentação da API
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  )
}