"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { getCurrentUser } from "@/lib/api/auth.api";
import { queryKeys } from "@/lib/api/query-keys";
import { useAppStore } from "@/store/useAppStore";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const setUser = useAppStore((state) => state.setUser);
  const user = useAppStore((state) => state.user);

  const authQuery = useQuery({
    queryKey: queryKeys.authMe,
    queryFn: getCurrentUser,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (authQuery.data) {
      setUser(authQuery.data);
    }
  }, [authQuery.data, setUser]);

  useEffect(() => {
    if (authQuery.isError) {
      setUser(null);
      router.replace("/auth/login");
      return;
    }

    if (!authQuery.isLoading && !authQuery.data) {
      router.replace("/auth/login");
    }
  }, [authQuery.data, authQuery.isError, authQuery.isLoading, router, setUser]);

  if (authQuery.isLoading || (!user && !authQuery.data)) {
    return null;
  }

  return <DashboardShell>{children}</DashboardShell>;
}
