"use client";

import { create } from "zustand";

import {
  PROCESSING_STEPS,
  type FilterState,
  type NotificationItem,
  type ProcessingState,
  type Project,
  type Task,
  type ThemeMode,
  type Transcript,
  type User,
} from "@/types";

interface PendingTranscript {
  projectId: string;
  content: string;
  transcriptId?: string;
}

// ────────────────────────────────────────────────────────────────
// CLEAN STATE INTERFACE - Single definition, no duplicates
// All data comes from backend API calls, not client-generated
// ────────────────────────────────────────────────────────────────

interface AppState {
  // State
  user: User | null;
  themeMode: ThemeMode;
  projects: Project[];
  tasks: Task[];
  selectedProject: string | null;
  filters: FilterState;
  notifications: NotificationItem[];
  transcripts: Transcript[];
  processingState: ProcessingState;
  pendingTranscript: PendingTranscript | null;
  activeTranscriptId: string | null;

  // Methods
  login: () => void;
  signup: () => void;
  setUser: (user: User | null) => void;
  setThemeMode: (mode: ThemeMode) => void;
  logout: () => void;
  setSelectedProject: (projectId: string | null) => void;
  setFilters: (filters: Partial<FilterState>) => void;
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  setTasks: (tasks: Task[]) => void;
  addProject: (project: Project) => void;
  updateProject: (projectId: string, updates: Partial<Project>) => void;
  setProjects: (projects: Project[]) => void;
  addNotification: (
    item: Omit<NotificationItem, "id" | "timestamp" | "read">,
  ) => void;
  markNotificationsRead: () => void;
  deleteNotification: (id: string) => void;
  addTranscript: (transcript: Transcript) => void;
  setTranscripts: (transcripts: Transcript[]) => void;
  setActiveTranscript: (transcriptId: string | null) => void;
  setProcessingState: (state: Partial<ProcessingState>) => void;
  startProcessing: (projectId: string, content: string) => Promise<void>;
  advanceProcessing: () => void;
  resetProcessing: () => void;
  completeProcessing: () => Promise<void>;
  cancelProcessing: () => void;
}

const THEME_STORAGE_KEY = "kanban-theme-mode";

const applyThemeMode = (themeMode: ThemeMode) => {
  if (typeof document === "undefined") {
    return;
  }
  document.documentElement.setAttribute("data-theme", themeMode);
};

const loadThemeMode = (): ThemeMode => {
  if (typeof window === "undefined") {
    return "light";
  }
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  return stored === "dark" ? "dark" : "light";
};

const initialFilters: FilterState = {
  sortByDate: "asc",
  onlyMine: false,
  onlyUnassigned: false,
  deadlineFilter: "all",
  customDate: null,
};

const initialProcessing: ProcessingState = {
  isProcessing: false,
  currentStep: 0,
  cancelled: false,
};

const initialThemeMode = loadThemeMode();
applyThemeMode(initialThemeMode);

export const useAppStore = create<AppState>((set, get) => ({
  // ─── Initial State ───
  user: null,
  themeMode: initialThemeMode,
  projects: [],
  tasks: [],
  selectedProject: null,
  filters: initialFilters,
  notifications: [],
  transcripts: [],
  processingState: initialProcessing,
  pendingTranscript: null,
  activeTranscriptId: null,

  // ─── Auth (moved to lib/auth.ts) ───
  login: () => {},
  signup: () => {},

  // ─── User Management ───
  setUser: (user) =>
    set((state) => {
      if (!user) {
        return {
          user: null,
          projects: [],
          tasks: [],
          selectedProject: null,
          transcripts: [],
          activeTranscriptId: null,
          pendingTranscript: null,
          processingState: initialProcessing,
        };
      }

      const isSwitchingUser = state.user?.id && user?.id && state.user.id !== user.id;
      if (!isSwitchingUser) {
        return { user };
      }

      // Clear user-scoped entities when switching accounts to avoid stale ID lookups.
      return {
        user,
        projects: [],
        tasks: [],
        selectedProject: null,
        transcripts: [],
        activeTranscriptId: null,
        pendingTranscript: null,
        processingState: initialProcessing,
      };
    }),
  logout: () =>
    set({
      user: null,
      projects: [],
      tasks: [],
      selectedProject: null,
      transcripts: [],
      activeTranscriptId: null,
      pendingTranscript: null,
      processingState: initialProcessing,
    }),

  // ─── Theme Management ───
  setThemeMode: (themeMode) => {
    applyThemeMode(themeMode);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(THEME_STORAGE_KEY, themeMode);
    }
    set({ themeMode });
  },

  // ─── Project Selection ───
  setSelectedProject: (projectId) => set({ selectedProject: projectId }),

  // ─── Filters ───
  setFilters: (filters) =>
    set((state) => ({
      filters: { ...state.filters, ...filters },
    })),

  // ─── Task Management ───
  addTask: (task) =>
    set((state) => {
      console.log("[Store] Adding task with backend ID:", task.id);
      return { tasks: [task, ...state.tasks] };
    }),

  updateTask: (taskId, updates) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === taskId ? { ...t, ...updates } : t,
      ),
    })),

  setTasks: (tasks) => set({ tasks }),

  // ─── Project Management ───
  addProject: (project) =>
    set((state) => ({
      projects: [project, ...state.projects],
      selectedProject: state.selectedProject ?? project.id,
    })),

  updateProject: (projectId, updates) =>
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === projectId ? { ...p, ...updates } : p,
      ),
    })),

  setProjects: (projects) => set({ projects }),

  // ─── Notifications ───
  addNotification: (item) =>
    set((state) => {
      const id = `notif-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      return {
        notifications: [
          {
            ...item,
            id,
            timestamp: new Date().toISOString(),
            read: false,
          },
          ...state.notifications,
        ],
      };
    }),

  markNotificationsRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
    })),

  deleteNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  // ─── Transcript Management ───
  addTranscript: (transcript) =>
    set((state) => ({
      transcripts: [transcript, ...state.transcripts],
    })),

  setTranscripts: (transcripts) => set({ transcripts }),

  setActiveTranscript: (transcriptId) =>
    set({ activeTranscriptId: transcriptId }),

  // ─── Processing State ───
  setProcessingState: (processing) =>
    set((state) => ({
      processingState: { ...state.processingState, ...processing },
    })),

  startProcessing: async (projectId: string, content: string) => {
    try {
      console.log("[Store] Creating transcript immediately...");

      const { createTranscriptApi } = await import("@/lib/tasks");
      const response = await createTranscriptApi({
        projectId,
        transcriptText: content,
        meetingTitle: "Transcript Upload",
      });

      set({
        pendingTranscript: { projectId, content, transcriptId: response.id },
        processingState: {
          isProcessing: true,
          currentStep: 0,
          cancelled: false,
        },
      });

      console.log("[Store] ✓ Transcript created with ID:", response.id);
    } catch (error) {
      console.error("[Store] ✗ Failed to create transcript:", error);
      throw error;
    }
  },

  advanceProcessing: () =>
    set((state) => {
      if (!state.processingState.isProcessing) {
        return state;
      }
      const nextStep = Math.min(
        state.processingState.currentStep + 1,
        PROCESSING_STEPS.length - 1,
      );
      return {
        processingState: {
          ...state.processingState,
          currentStep: nextStep,
        },
      };
    }),

  resetProcessing: () =>
    set({
      processingState: initialProcessing,
      pendingTranscript: null,
    }),

  cancelProcessing: () =>
    set((state) => ({
      processingState: {
        ...state.processingState,
        cancelled: true,
        isProcessing: false,
      },
      pendingTranscript: null,
    })),

  // ─── Transcript Upload & Processing ───
  completeProcessing: async () => {
    const { pendingTranscript, addNotification } = get();

    if (!pendingTranscript || !pendingTranscript.transcriptId) {
      set({ processingState: initialProcessing });
      return;
    }

    try {
      console.log("[Store] Fetching completed transcript data...");

      const { getTranscriptStatusApi } = await import("@/lib/tasks");
      const response = await getTranscriptStatusApi(
        pendingTranscript.transcriptId,
      );

      const transcript: Transcript = {
        id: response.id,
        projectId: pendingTranscript.projectId,
        content: pendingTranscript.content,
        summary: response.summary || "",
        createdAt: new Date().toISOString(),
        actionItemIds: response.actionItemIds || [],
        actionItems: response.actionItems || [],
      };

      set((state) => ({
        transcripts: [transcript, ...state.transcripts],
        activeTranscriptId: transcript.id,
        pendingTranscript: null,
        processingState: initialProcessing,
      }));

      addNotification({
        message: "Transcript processed successfully",
        type: "success",
      });

      console.log("[Store] ✓ Transcript processing completed");
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error("[Store] Failed to complete processing:", msg);

      get().addNotification({
        message: `Failed: ${msg}`,
        type: "warning",
      });

      set({
        pendingTranscript: null,
        processingState: initialProcessing,
      });
    }
  },
}));
