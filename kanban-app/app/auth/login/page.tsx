"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { BrandLogo } from "@/components/shared/BrandLogo";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { warmupBackend } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import * as authApi from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const setUser = useAppStore((state) => state.setUser);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void warmupBackend();
  }, []);

  const canSubmit = useMemo(
    () => email.trim().includes("@") && password.trim().length >= 8,
    [email, password],
  );

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit || loading) {
      return;
    }

    setError("");
    setLoading(true);

    try {
      const result = await authApi.login({ email, password });
      setUser(result.user);
      router.replace("/dashboard/kanban");
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Login failed. Please try again.";
      setError(errorMsg);
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-3">
          <div className="mx-auto rounded-xl border border-border/80 bg-muted/50 p-3">
            <BrandLogo variant="full" className="h-9 w-auto px-1 py-1" />
          </div>
          <CardTitle className="text-3xl font-semibold">Login</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            {error && (
              <div className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-danger">
                <p className="text-sm">{error}</p>
              </div>
            )}

            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                disabled={loading}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={loading}
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={!canSubmit || loading}
            >
              {loading ? "Logging in..." : "Login"}
            </Button>
          </form>

          <p className="mt-4 text-sm text-text-secondary">
            New here?{" "}
            <Link
              href="/auth/signup"
              className="font-medium text-text-primary underline"
            >
              Create an account
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
