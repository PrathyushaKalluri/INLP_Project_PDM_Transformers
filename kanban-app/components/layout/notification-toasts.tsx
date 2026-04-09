"use client";

import { useEffect, useRef } from "react";

import { useToast } from "@/components/ui/use-toast";
import { useAppStore } from "@/store/useAppStore";

export function NotificationToasts() {
  const notifications = useAppStore((state) => state.notifications);
  const { toast } = useToast();
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
