import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import { normalizeApiError } from "@/lib/api/client";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const getErrorMessage = (error: unknown) => normalizeApiError(error).message;
