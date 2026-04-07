"use client";

import { useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";

import { useToast } from "@/components/ui/use-toast";
import { getNotifications } from "@/lib/api/notifications.api";
import { queryKeys } from "@/lib/api/query-keys";

export function NotificationToasts() {
  const { toast } = useToast();
  const notificationsQuery = useQuery({
    queryKey: queryKeys.notifications,
    queryFn: getNotifications,
  });
  const notifications = useMemo(() => notificationsQuery.data ?? [], [notificationsQuery.data]);
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (seen.current.size === 0) {
      notifications.forEach((item) => seen.current.add(item.id));
      return;
    }

    notifications.forEach((item) => {
      if (seen.current.has(item.id)) {
        return;
      }

      seen.current.add(item.id);
      toast({
        title: "New activity",
        description: item.message,
      });
    });
  }, [notifications, toast]);

  return null;
}
