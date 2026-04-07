"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { signup } from "@/lib/api/auth.api";
import { queryKeys } from "@/lib/api/query-keys";
import { getErrorMessage } from "@/lib/utils";
import { BrandLogo } from "@/components/shared/BrandLogo";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import { useAppStore } from "@/store/useAppStore";

export default function SignupPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const setUser = useAppStore((state) => state.setUser);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [inlineError, setInlineError] = useState<string | null>(null);

  const signupMutation = useMutation({
    mutationFn: signup,
    onSuccess: (user) => {
      setInlineError(null);
      setUser(user);
      queryClient.setQueryData(queryKeys.authMe, user);
      router.replace("/dashboard/kanban");
    },
    onError: (error) => {
      const message = getErrorMessage(error);
      setInlineError(message);
      toast({
        title: "Signup failed",
        description: message,
      });
    },
  });

  const canSubmit = useMemo(
    () =>
      email.trim().includes("@") &&
      password.trim().length >= 6 &&
      confirmPassword.trim().length >= 6 &&
      password === confirmPassword,
    [email, password, confirmPassword]
  );

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }

    await signupMutation.mutateAsync({
      email: email.trim(),
      password,
    });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-3">
          <div className="mx-auto rounded-xl border border-border/80 bg-muted/50 p-3">
            <BrandLogo variant="full" className="h-9 w-auto px-1 py-1" />
          </div>
          <CardTitle className="text-3xl font-semibold">Signup</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Minimum 6 characters"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="confirm-password">Confirm Password</Label>
              <Input
                id="confirm-password"
                type="password"
                placeholder="Re-enter password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={!canSubmit || signupMutation.isPending}
            >
              Signup
            </Button>
            {inlineError ? <p className="text-sm text-danger">{inlineError}</p> : null}
          </form>

          <p className="mt-4 text-sm text-text-secondary">
            Already have an account?{" "}
            <Link href="/auth/login" className="font-medium text-text-primary underline">
              Login
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
