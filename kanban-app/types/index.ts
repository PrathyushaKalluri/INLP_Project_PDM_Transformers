export type Role = "manager" | "member";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar: string;
}

export interface Project {
  id: string;
  teamId?: string;
  name: string;
  description: string;
  participants: string[];
}

export type TaskStatus = "todo" | "in-progress" | "completed";

export type ThemeMode = "light" | "dark";

export interface Task {
  id: string;
  projectId: string;
  title: string;
  description: string;
  deadline: string;
  assigneeIds: string[];
  transcriptReference: string;
  status: TaskStatus;
}

export interface FilterState {
  sortByDate: "asc" | "desc";
  onlyMine: boolean;
  deadlineFilter: "all" | "today" | "near" | "overdue";
  customDate: string | null;
}

export interface NotificationItem {
  id: string;
  message: string;
  timestamp: string;
  type: "info" | "success" | "warning";
  read: boolean;
}

export interface Transcript {
  id: string;
  projectId: string;
  content: string;
  summary: string;
  createdAt: string;
  actionItemIds: string[];
  actionItems: {
    title: string;
    description?: string;
    assignee?: string;
    deadline?: string;
  }[];
}

export interface ProcessingState {
  isProcessing: boolean;
  currentStep: number;
  cancelled: boolean;
}

export const PROCESSING_STEPS = [
  "Analyzing transcript...",
  "Parsing transcript",
  "Extracting action items",
  "Generating summary",
] as const;
