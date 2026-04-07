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

  const topLeftSoftDots = [
    { top: "8%", left: "10%", tone: "bg-border", opacity: "opacity-40" },
    { top: "20%", left: "28%", tone: "bg-primary", opacity: "opacity-40" },
    { top: "34%", left: "14%", tone: "bg-border", opacity: "opacity-60" },
    { top: "46%", left: "38%", tone: "bg-border", opacity: "opacity-40" },
    { top: "62%", left: "24%", tone: "bg-primary", opacity: "opacity-40" },
    { top: "76%", left: "42%", tone: "bg-border", opacity: "opacity-60" },
  ];

  const topLeftSharpDots = [
    { top: "14%", left: "42%", tone: "bg-primary", opacity: "opacity-60" },
    { top: "30%", left: "54%", tone: "bg-border", opacity: "opacity-80" },
    { top: "52%", left: "60%", tone: "bg-primary", opacity: "opacity-60" },
    { top: "68%", left: "50%", tone: "bg-border", opacity: "opacity-60" },
  ];

  const midLeftSoftDots = [
    { top: "6%", left: "8%", tone: "bg-border", opacity: "opacity-40" },
    { top: "18%", left: "26%", tone: "bg-primary", opacity: "opacity-40" },
    { top: "28%", left: "44%", tone: "bg-border", opacity: "opacity-60" },
    { top: "42%", left: "16%", tone: "bg-border", opacity: "opacity-40" },
    { top: "50%", left: "34%", tone: "bg-primary", opacity: "opacity-60" },
    { top: "64%", left: "22%", tone: "bg-border", opacity: "opacity-40" },
    { top: "74%", left: "48%", tone: "bg-primary", opacity: "opacity-40" },
    { top: "86%", left: "30%", tone: "bg-border", opacity: "opacity-60" },
  ];

  const midLeftSharpDots = [
    { top: "14%", left: "60%", tone: "bg-primary", opacity: "opacity-80" },
    { top: "24%", left: "72%", tone: "bg-border", opacity: "opacity-60" },
    { top: "40%", left: "64%", tone: "bg-primary", opacity: "opacity-60" },
    { top: "58%", left: "74%", tone: "bg-border", opacity: "opacity-80" },
    { top: "72%", left: "66%", tone: "bg-primary", opacity: "opacity-60" },
    { top: "90%", left: "78%", tone: "bg-border", opacity: "opacity-60" },
  ];

  const bottomRightSoftDots = [
    { top: "6%", left: "18%", tone: "bg-border", opacity: "opacity-40" },
    { top: "14%", left: "38%", tone: "bg-primary", opacity: "opacity-40" },
    { top: "20%", left: "58%", tone: "bg-border", opacity: "opacity-60" },
    { top: "30%", left: "78%", tone: "bg-primary", opacity: "opacity-40" },
    { top: "42%", left: "28%", tone: "bg-border", opacity: "opacity-60" },
    { top: "48%", left: "50%", tone: "bg-primary", opacity: "opacity-40" },
    { top: "56%", left: "72%", tone: "bg-border", opacity: "opacity-60" },
    { top: "66%", left: "20%", tone: "bg-primary", opacity: "opacity-40" },
    { top: "72%", left: "42%", tone: "bg-border", opacity: "opacity-60" },
    { top: "80%", left: "62%", tone: "bg-primary", opacity: "opacity-40" },
    { top: "88%", left: "82%", tone: "bg-border", opacity: "opacity-60" },
  ];

  const bottomRightSharpDots = [
    { top: "10%", left: "66%", tone: "bg-primary", opacity: "opacity-80" },
    { top: "24%", left: "86%", tone: "bg-border", opacity: "opacity-60" },
    { top: "38%", left: "62%", tone: "bg-primary", opacity: "opacity-60" },
    { top: "52%", left: "84%", tone: "bg-border", opacity: "opacity-80" },
    { top: "68%", left: "74%", tone: "bg-primary", opacity: "opacity-80" },
    { top: "84%", left: "58%", tone: "bg-border", opacity: "opacity-60" },
  ];

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
      <div className="pointer-events-none absolute left-4 top-16 hidden h-52 w-56 md:block">
        <div className="absolute inset-0 blur-[0.5px]">
          {topLeftSoftDots.map((dot, idx) => (
            <span
              key={`top-left-soft-${idx}`}
              className={`absolute h-2.5 w-2.5 rounded-full md:h-3 md:w-3 ${dot.tone} ${dot.opacity}`}
              style={{ top: dot.top, left: dot.left }}
            />
          ))}
        </div>
        <div className="absolute inset-0">
          {topLeftSharpDots.map((dot, idx) => (
            <span
              key={`top-left-sharp-${idx}`}
              className={`absolute h-2.5 w-2.5 rounded-full md:h-3 md:w-3 ${dot.tone} ${dot.opacity}`}
              style={{ top: dot.top, left: dot.left }}
            />
          ))}
        </div>
      </div>

      <div className="pointer-events-none absolute left-2 top-[34%] hidden h-64 w-64 md:block lg:left-8">
        <div className="absolute inset-0 blur-[0.5px]">
          {midLeftSoftDots.map((dot, idx) => (
            <span
              key={`mid-left-soft-${idx}`}
              className={`absolute h-2.5 w-2.5 rounded-full md:h-3 md:w-3 ${dot.tone} ${dot.opacity}`}
              style={{ top: dot.top, left: dot.left }}
            />
          ))}
        </div>
        <div className="absolute inset-0">
          {midLeftSharpDots.map((dot, idx) => (
            <span
              key={`mid-left-sharp-${idx}`}
              className={`absolute h-2.5 w-2.5 rounded-full md:h-3 md:w-3 ${dot.tone} ${dot.opacity}`}
              style={{ top: dot.top, left: dot.left }}
            />
          ))}
        </div>
      </div>

      <div className="pointer-events-none absolute bottom-8 right-2 h-56 w-64 md:right-6 md:h-72 md:w-80">
        <div className="absolute inset-0 blur-[0.5px]">
          {bottomRightSoftDots.map((dot, idx) => (
            <span
              key={`bottom-right-soft-${idx}`}
              className={`absolute h-2.5 w-2.5 rounded-full md:h-3 md:w-3 ${dot.tone} ${dot.opacity}`}
              style={{ top: dot.top, left: dot.left }}
            />
          ))}
        </div>
        <div className="absolute inset-0">
          {bottomRightSharpDots.map((dot, idx) => (
            <span
              key={`bottom-right-sharp-${idx}`}
              className={`absolute h-2.5 w-2.5 rounded-full md:h-3 md:w-3 ${dot.tone} ${dot.opacity}`}
              style={{ top: dot.top, left: dot.left }}
            />
          ))}
        </div>
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
