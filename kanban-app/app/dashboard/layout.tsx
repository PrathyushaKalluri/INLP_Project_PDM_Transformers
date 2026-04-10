"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { getMe } from "@/lib/auth";
import { clearTokens, getAccessToken } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const user = useAppStore((state) => state.user);
  const setUser = useAppStore((state) => state.setUser);
  const [bootstrapping, setBootstrapping] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const bootstrapSession = async () => {
      if (user) {
        if (!cancelled) {
          setBootstrapping(false);
        }
        return;
      }

      const accessToken = getAccessToken();
      if (!accessToken) {
        if (!cancelled) {
          setBootstrapping(false);
          router.replace("/auth/login");
        }
        return;
      }

      try {
        const currentUser = await getMe();
        if (!cancelled) {
          setUser(currentUser);
          setBootstrapping(false);
        }
      } catch {
        clearTokens();
        if (!cancelled) {
          setUser(null);
          setBootstrapping(false);
          router.replace("/auth/login");
        }
      }
    };

    bootstrapSession();

    return () => {
      cancelled = true;
    };
  }, [user, router, setUser]);

  useEffect(() => {
    if (!bootstrapping && !user) {
      router.replace("/auth/login");
    }
  }, [bootstrapping, user, router]);

  if (bootstrapping || !user) {
    return null;
  }

  return <DashboardShell>{children}</DashboardShell>;
}
