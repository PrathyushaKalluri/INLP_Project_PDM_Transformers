"use client";

import { Bell } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAppStore } from "@/store/useAppStore";

export function NotificationsPanel() {
  const notifications = useAppStore((state) => state.notifications);
  const markNotificationsRead = useAppStore((state) => state.markNotificationsRead);

  const unread = notifications.filter((item) => !item.read).length;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="secondary" size="icon" className="relative">
          <Bell className="h-4 w-4" />
          {unread > 0 ? (
            <span className="absolute -top-1 -right-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-danger px-1 text-xs text-danger-contrast">
              {unread}
            </span>
          ) : null}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[22rem]">
        <div className="flex items-center justify-between p-1">
          <DropdownMenuLabel>Notifications</DropdownMenuLabel>
          <Button variant="ghost" size="sm" onClick={markNotificationsRead}>
            Mark all read
          </Button>
        </div>
        <DropdownMenuSeparator />
        <ScrollArea className="h-72">
          <div className="space-y-2 p-1 pr-3">
            {notifications.length === 0 ? (
              <p className="rounded-xl border border-dashed border-border p-3 text-sm text-text-secondary">
                No notifications yet.
              </p>
            ) : (
              notifications.map((item) => (
                <div
                  key={item.id}
                  className={`rounded-xl border p-3 ${
                    item.read ? "border-border bg-card" : "border-primary/40 bg-primary/10"
                  }`}
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <Badge
                      variant={
                        item.type === "success"
                          ? "primary"
                          : item.type === "warning"
                            ? "warning"
                            : "default"
                      }
                    >
                      {item.type}
                    </Badge>
                    <span className="text-xs text-text-secondary">
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-sm text-text-primary">{item.message}</p>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
