"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { BrandLogo } from "@/components/shared/BrandLogo";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getCurrentUser } from "@/lib/api/auth.api";
import { queryKeys } from "@/lib/api/query-keys";

export function HeroSection() {
  const router = useRouter();

  const authQuery = useQuery({
    queryKey: queryKeys.authMe,
    queryFn: getCurrentUser,
    retry: false,
  });

  useEffect(() => {
    if (authQuery.data) {
      router.replace("/dashboard/kanban");
    }
  }, [authQuery.data, router]);

  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-gradient-to-b from-[#0F0F1A] via-[#12121F] to-[#0B0B14] before:absolute before:inset-0 before:bg-[radial-gradient(circle_at_center,rgba(230,165,126,0.08),transparent_70%)] before:content-['']">
      <div className="pointer-events-none absolute left-6 top-24 hidden grid-cols-6 gap-2 opacity-40 blur-[0.5px] md:grid">
        {Array.from({ length: 30 }).map((_, idx) => (
          <span
            key={`left-dot-${idx}`}
            className={`h-2.5 w-2.5 rounded-full ${idx % 4 === 0 ? "bg-primary" : "bg-border"}`}
          />
        ))}
      </div>

      <div className="pointer-events-none absolute bottom-8 right-6 grid grid-cols-7 gap-2 opacity-40 blur-[0.5px]">
        {Array.from({ length: 35 }).map((_, idx) => (
          <span
            key={`right-dot-${idx}`}
            className={`h-2 w-2 rounded-full ${idx % 5 === 0 ? "bg-primary" : "bg-text-secondary/40"}`}
          />
        ))}
      </div>

      <section className="relative z-10 flex min-h-screen flex-col items-center justify-center gap-6 px-4 text-center">
        <BrandLogo variant="full" className="mx-auto mb-6 h-12 w-auto md:h-16" />

        <Badge
          variant="default"
          className="rounded-full border border-border bg-muted px-3 py-1 text-xs text-text-secondary"
        >
          New features released
        </Badge>

        <h1 className="text-4xl font-semibold leading-tight tracking-tight text-white md:text-6xl">
          Make Better Decisions,
          <br />
          With Ease
        </h1>

        <p className="mx-auto max-w-xl text-base leading-relaxed text-text-secondary md:text-lg">
          Makezy&apos;s personal AI helps people turn meeting conversations into clear, actionable
          tasks, making it easier to stay organized, collaborate effectively, and keep work moving
          without losing focus.
        </p>

        <Button
          size="lg"
          className="bg-blue-600 px-6 py-3 text-sm font-medium text-white shadow-md transition-all hover:scale-[1.02] hover:bg-blue-700 md:text-base"
          onClick={() => router.push("/auth/login")}
        >
          Get started
        </Button>

        <div className="mt-2 flex items-center justify-center gap-2">
          <div className="flex -space-x-2">
            <Avatar className="border border-[#0B0B14]">
              <AvatarFallback>AL</AvatarFallback>
            </Avatar>
            <Avatar className="border border-[#0B0B14]">
              <AvatarFallback>RM</AvatarFallback>
            </Avatar>
            <Avatar className="border border-[#0B0B14]">
              <AvatarFallback>SK</AvatarFallback>
            </Avatar>
          </div>
          <span className="text-sm text-text-secondary">Loved by 4200+ professionals</span>
        </div>
      </section>
    </main>
  );
}
