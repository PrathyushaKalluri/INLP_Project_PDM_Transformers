import { z } from "zod";

import { apiClient, parseWithSchema } from "@/lib/api/client";
import type { NotificationItem } from "@/types";

const notificationSchema = z.object({
  id: z.string(),
  message: z.string(),
  timestamp: z.string(),
  type: z.enum(["info", "success", "warning"]),
  read: z.boolean(),
});

const notificationsSchema = z.array(notificationSchema);

export async function getNotifications(): Promise<NotificationItem[]> {
  const response = await apiClient.get("/notifications");
  return parseWithSchema(notificationsSchema, response.data, "Invalid notifications response");
}

export async function markNotificationsRead(notificationIds?: string[]) {
  await apiClient.post("/notifications/read", {
    notificationIds,
  });
}
