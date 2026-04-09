"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { useAppStore } from "@/store/useAppStore";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const user = useAppStore((state) => state.user);

  useEffect(() => {
    if (!user) {
      router.replace("/auth/login");
    }
  }, [user, router]);

  if (!user) {
    return null;
  }

  return <DashboardShell>{children}</DashboardShell>;
}
