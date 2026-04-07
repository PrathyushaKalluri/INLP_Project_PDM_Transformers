"use client";

import { create } from "zustand";

import type { FilterState, ProcessingState, ThemeMode, User } from "@/types";

interface ProcessingUiState extends ProcessingState {
  jobId: string | null;
  transcriptId: string | null;
  lastError: string | null;
}

interface AppState {
  user: User | null;
  themeMode: ThemeMode;
  selectedProject: string | null;
  filters: FilterState;
  activeTranscriptId: string | null;
  processingState: ProcessingUiState;
  setUser: (user: User | null) => void;
  setThemeMode: (themeMode: ThemeMode) => void;
  logoutLocal: () => void;
  setSelectedProject: (projectId: string | null) => void;
  setFilters: (filters: Partial<FilterState>) => void;
  setActiveTranscript: (transcriptId: string | null) => void;
  startProcessing: (jobId: string, transcriptId: string) => void;
  setProcessingStep: (step: number) => void;
  completeProcessing: () => void;
  cancelProcessingLocal: () => void;
  failProcessing: (message: string) => void;
  resetProcessing: () => void;
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
  deadlineFilter: "all",
  customDate: null,
};

const initialProcessingState: ProcessingUiState = {
  isProcessing: false,
  currentStep: 0,
  cancelled: false,
  jobId: null,
  transcriptId: null,
  lastError: null,
};

const initialThemeMode = loadThemeMode();
applyThemeMode(initialThemeMode);

export const useAppStore = create<AppState>((set) => ({
  user: null,
  themeMode: initialThemeMode,
  selectedProject: null,
  filters: initialFilters,
  activeTranscriptId: null,
  processingState: initialProcessingState,

  setUser: (user) => set({ user }),

  setThemeMode: (themeMode) => {
    applyThemeMode(themeMode);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(THEME_STORAGE_KEY, themeMode);
    }
    set({ themeMode });
  },

  logoutLocal: () =>
    set({
      user: null,
      activeTranscriptId: null,
      processingState: initialProcessingState,
    }),

  setSelectedProject: (projectId) => set({ selectedProject: projectId }),

  setFilters: (filters) =>
    set((state) => ({
      filters: {
        ...state.filters,
        ...filters,
      },
    })),

  setActiveTranscript: (transcriptId) => set({ activeTranscriptId: transcriptId }),

  startProcessing: (jobId, transcriptId) =>
    set({
      processingState: {
        isProcessing: true,
        currentStep: 0,
        cancelled: false,
        jobId,
        transcriptId,
        lastError: null,
      },
    }),

  setProcessingStep: (step) =>
    set((state) => ({
      processingState: {
        ...state.processingState,
        currentStep: step,
      },
    })),

  completeProcessing: () =>
    set((state) => ({
      processingState: {
        ...state.processingState,
        isProcessing: false,
        cancelled: false,
      },
    })),

  cancelProcessingLocal: () =>
    set((state) => ({
      processingState: {
        ...state.processingState,
        isProcessing: false,
        cancelled: true,
      },
    })),

  failProcessing: (message) =>
    set((state) => ({
      processingState: {
        ...state.processingState,
        isProcessing: false,
        cancelled: false,
        lastError: message,
      },
    })),

  resetProcessing: () => set({ processingState: initialProcessingState }),
}));
