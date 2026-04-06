"use client";

import { create } from "zustand";

import {
  PROCESSING_STEPS,
  type FilterState,
  type NotificationItem,
  type ProcessingState,
  type Project,
  type Task,
  type TaskStatus,
  type ThemeMode,
  type Transcript,
  type User,
} from "@/types";

interface PendingTranscript {
  projectId: string;
  content: string;
}

interface AppState {
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
  login: (email: string) => void;
  signup: (email: string, name?: string) => void;
  setUser: (user: User | null) => void;
  setThemeMode: (themeMode: ThemeMode) => void;
  logout: () => void;
  setSelectedProject: (projectId: string) => void;
  setFilters: (filters: Partial<FilterState>) => void;
  addTask: (task: Omit<Task, "id">) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  addProject: (project: Omit<Project, "id">) => void;
  updateProject: (projectId: string, updates: Partial<Project>) => void;
  addNotification: (item: Omit<NotificationItem, "id" | "timestamp" | "read">) => void;
  markNotificationsRead: () => void;
  setActiveTranscript: (transcriptId: string | null) => void;
  updateTranscript: (transcriptId: string, updates: Partial<Transcript>) => void;
  startProcessing: (projectId: string, content: string) => void;
  advanceProcessing: () => void;
  cancelProcessing: () => void;
  resetProcessing: () => void;
  completeProcessing: () => void;
}

const uid = () =>
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

const dayShift = (days: number) => {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
};

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

const mockUsers: User[] = [
  {
    id: "u-1",
    name: "Aarav Sharma",
    email: "aarav@acme.ai",
    role: "manager",
    avatar: "AS",
  },
  {
    id: "u-2",
    name: "Nitya Kapoor",
    email: "nitya@acme.ai",
    role: "member",
    avatar: "NK",
  },
  {
    id: "u-3",
    name: "Rohan Iyer",
    email: "rohan@acme.ai",
    role: "member",
    avatar: "RI",
  },
  {
    id: "u-4",
    name: "Zoya Mehta",
    email: "zoya@acme.ai",
    role: "member",
    avatar: "ZM",
  },
];

const mockProjects: Project[] = [
  {
    id: "p-1",
    name: "Onboarding Revamp",
    description: "Improve first-run activation and reduce drop-off.",
    participants: ["u-1", "u-2", "u-3"],
  },
  {
    id: "p-2",
    name: "Mobile Sprint Q2",
    description: "Responsive adaptation and usability issues from QA.",
    participants: ["u-1", "u-2", "u-4"],
  },
  {
    id: "p-3",
    name: "Ops Automation",
    description: "Automate recurring customer support workflows.",
    participants: ["u-1", "u-3", "u-4"],
  },
];

const mockTasks: Task[] = [
  {
    id: "t-1",
    projectId: "p-1",
    title: "Map first-session friction points",
    description: "Review call recordings and identify confusion moments.",
    deadline: dayShift(3),
    assigneeIds: ["u-2"],
    transcriptReference: "TR-ONB-214",
    status: "todo",
  },
  {
    id: "t-2",
    projectId: "p-1",
    title: "Draft guided setup copy",
    description: "Prepare concise helper text for setup steps.",
    deadline: dayShift(1),
    assigneeIds: ["u-3"],
    transcriptReference: "TR-ONB-217",
    status: "in-progress",
  },
  {
    id: "t-3",
    projectId: "p-1",
    title: "Align success metrics",
    description: "Finalize activation KPI definition with product lead.",
    deadline: dayShift(-1),
    assigneeIds: ["u-1", "u-2"],
    transcriptReference: "TR-ONB-209",
    status: "completed",
  },
  {
    id: "t-4",
    projectId: "p-2",
    title: "Tablet nav regression fixes",
    description: "Resolve sidebar overlap and touch target issues.",
    deadline: dayShift(0),
    assigneeIds: ["u-4"],
    transcriptReference: "TR-MOB-039",
    status: "todo",
  },
  {
    id: "t-5",
    projectId: "p-2",
    title: "Hero performance baseline",
    description: "Capture LCP/FCP benchmarks before redesign.",
    deadline: dayShift(5),
    assigneeIds: ["u-2", "u-4"],
    transcriptReference: "TR-MOB-041",
    status: "in-progress",
  },
  {
    id: "t-6",
    projectId: "p-3",
    title: "Ticket auto-routing policy",
    description: "Define rules for high-priority incident triaging.",
    deadline: dayShift(2),
    assigneeIds: ["u-3"],
    transcriptReference: "TR-OPS-122",
    status: "todo",
  },
  {
    id: "t-7",
    projectId: "p-1",
    title: "Rewrite account permissions tooltip",
    description: "Clarify scope and remove ambiguous access wording.",
    deadline: dayShift(4),
    assigneeIds: ["u-2"],
    transcriptReference: "TR-ONB-231",
    status: "todo",
  },
  {
    id: "t-8",
    projectId: "p-1",
    title: "Prototype progressive profile form",
    description: "Break profile setup into two lightweight screens.",
    deadline: dayShift(6),
    assigneeIds: ["u-1", "u-3"],
    transcriptReference: "TR-ONB-232",
    status: "todo",
  },
  {
    id: "t-9",
    projectId: "p-1",
    title: "Instrument drop-off events",
    description: "Track abandonment on each onboarding step.",
    deadline: dayShift(2),
    assigneeIds: ["u-3"],
    transcriptReference: "TR-ONB-233",
    status: "in-progress",
  },
  {
    id: "t-10",
    projectId: "p-1",
    title: "Audit first-email timing",
    description: "Validate send window against timezone cohorts.",
    deadline: dayShift(1),
    assigneeIds: ["u-1", "u-4"],
    transcriptReference: "TR-ONB-236",
    status: "in-progress",
  },
  {
    id: "t-11",
    projectId: "p-1",
    title: "Prepare empty-state illustration brief",
    description: "Share references and copy direction with design.",
    deadline: dayShift(8),
    assigneeIds: ["u-4"],
    transcriptReference: "TR-ONB-240",
    status: "todo",
  },
  {
    id: "t-12",
    projectId: "p-1",
    title: "Review welcome flow with support team",
    description: "Collect recurring ticket topics from first-week users.",
    deadline: dayShift(-2),
    assigneeIds: ["u-1", "u-2"],
    transcriptReference: "TR-ONB-225",
    status: "completed",
  },
  {
    id: "t-13",
    projectId: "p-1",
    title: "Consolidate setup checklist",
    description: "Merge duplicate setup prompts into one checklist module.",
    deadline: dayShift(7),
    assigneeIds: ["u-2", "u-3"],
    transcriptReference: "TR-ONB-241",
    status: "todo",
  },
  {
    id: "t-14",
    projectId: "p-1",
    title: "QA pass for low-vision users",
    description: "Run high contrast and keyboard navigation checks.",
    deadline: dayShift(3),
    assigneeIds: ["u-4"],
    transcriptReference: "TR-ONB-244",
    status: "in-progress",
  },
  {
    id: "t-15",
    projectId: "p-1",
    title: "Ship onboarding copy v2",
    description: "Publish approved copy updates behind experiment flag.",
    deadline: dayShift(-3),
    assigneeIds: ["u-1", "u-3"],
    transcriptReference: "TR-ONB-220",
    status: "completed",
  },
  {
    id: "t-16",
    projectId: "p-2",
    title: "Android keyboard overlap investigation",
    description: "Reproduce and patch viewport jump in task modal.",
    deadline: dayShift(2),
    assigneeIds: ["u-2"],
    transcriptReference: "TR-MOB-045",
    status: "todo",
  },
  {
    id: "t-17",
    projectId: "p-2",
    title: "Reduce startup bundle size",
    description: "Split dashboard widgets and defer non-critical modules.",
    deadline: dayShift(4),
    assigneeIds: ["u-1", "u-4"],
    transcriptReference: "TR-MOB-049",
    status: "in-progress",
  },
  {
    id: "t-18",
    projectId: "p-2",
    title: "Close swipe gesture parity gaps",
    description: "Align iOS and Android behavior for list interactions.",
    deadline: dayShift(-1),
    assigneeIds: ["u-4"],
    transcriptReference: "TR-MOB-050",
    status: "completed",
  },
  {
    id: "t-19",
    projectId: "p-3",
    title: "Define incident tagging taxonomy",
    description: "Standardize labels for escalations and routing rules.",
    deadline: dayShift(1),
    assigneeIds: ["u-3", "u-4"],
    transcriptReference: "TR-OPS-124",
    status: "todo",
  },
  {
    id: "t-20",
    projectId: "p-3",
    title: "Build support queue dashboard",
    description: "Surface SLA drift and owner workloads in one view.",
    deadline: dayShift(5),
    assigneeIds: ["u-1", "u-3"],
    transcriptReference: "TR-OPS-128",
    status: "in-progress",
  },
  {
    id: "t-21",
    projectId: "p-3",
    title: "Automate overdue ticket reminders",
    description: "Schedule follow-ups for unresolved P1 conversations.",
    deadline: dayShift(-4),
    assigneeIds: ["u-2"],
    transcriptReference: "TR-OPS-131",
    status: "completed",
  },
  {
    id: "t-22",
    projectId: "p-1",
    title: "Run onboarding copy localization review",
    description: "Flag terms that break clarity in Hindi and Tamil variants.",
    deadline: dayShift(9),
    assigneeIds: ["u-2", "u-4"],
    transcriptReference: "TR-ONB-249",
    status: "todo",
  },
  {
    id: "t-23",
    projectId: "p-1",
    title: "Validate event naming conventions",
    description: "Ensure analytics events align with product measurement spec.",
    deadline: dayShift(6),
    assigneeIds: ["u-1", "u-3"],
    transcriptReference: "TR-ONB-252",
    status: "todo",
  },
  {
    id: "t-24",
    projectId: "p-1",
    title: "Usability playback synthesis",
    description: "Summarize recurring hesitation patterns from test sessions.",
    deadline: dayShift(4),
    assigneeIds: ["u-3"],
    transcriptReference: "TR-ONB-254",
    status: "in-progress",
  },
];

const initialFilters: FilterState = {
  sortByDate: "asc",
  onlyMine: false,
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

const splitTranscript = (content: string) => {
  const chunks = content
    .split(/[\n.]/)
    .map((line) => line.trim())
    .filter(Boolean);

  return chunks.slice(0, 3);
};

const statusFromIndex = (index: number): TaskStatus => {
  if (index === 0) {
    return "todo";
  }
  if (index === 1) {
    return "in-progress";
  }
  return "completed";
};

export const useAppStore = create<AppState>((set, get) => ({
  user: mockUsers[0],
  themeMode: initialThemeMode,
  projects: mockProjects,
  tasks: mockTasks,
  selectedProject: mockProjects[0]?.id ?? null,
  filters: initialFilters,
  notifications: [
    {
      id: "n-1",
      message: "Nitya updated onboarding task dependencies.",
      timestamp: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
      type: "info",
      read: false,
    },
    {
      id: "n-2",
      message: "Weekly mobile sprint summary was published.",
      timestamp: new Date(Date.now() - 1000 * 60 * 80).toISOString(),
      type: "success",
      read: true,
    },
  ],
  transcripts: [
    {
      id: "tr-1",
      projectId: "p-1",
      content:
        "We need to simplify setup, shorten the first form and assign copy review to the content team.",
      summary:
        "Team aligned on reducing onboarding friction by simplifying setup flow and tightening guidance copy.",
      createdAt: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
      actionItemIds: ["t-1", "t-2"],
    },
  ],
  processingState: initialProcessing,
  pendingTranscript: null,
  activeTranscriptId: "tr-1",

  login: (email) => {
    const existing = mockUsers.find((user) => user.email === email.trim().toLowerCase());
    if (existing) {
      set({ user: existing });
      return;
    }

    set({ user: mockUsers[0] });
  },

  signup: (email, name) => {
    const normalizedEmail = email.trim().toLowerCase();
    const existing = mockUsers.find((user) => user.email === normalizedEmail);
    if (existing) {
      set({ user: existing });
      return;
    }

    const newUser: User = {
      id: uid(),
      name: name?.trim() || normalizedEmail.split("@")[0] || "New User",
      email: normalizedEmail,
      role: "member",
      avatar: (name?.trim() || normalizedEmail)
        .split(" ")
        .map((chunk) => chunk[0])
        .join("")
        .slice(0, 2)
        .toUpperCase(),
    };

    mockUsers.push(newUser);
    set({ user: newUser });
  },

  setUser: (user) => set({ user }),

  setThemeMode: (themeMode) => {
    applyThemeMode(themeMode);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(THEME_STORAGE_KEY, themeMode);
    }
    set({ themeMode });
  },

  logout: () => set({ user: null }),

  setSelectedProject: (projectId) => set({ selectedProject: projectId }),

  setFilters: (filters) =>
    set((state) => ({
      filters: {
        ...state.filters,
        ...filters,
      },
    })),

  addTask: (task) =>
    set((state) => ({
      tasks: [{ ...task, id: uid() }, ...state.tasks],
    })),

  updateTask: (taskId, updates) =>
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === taskId ? { ...task, ...updates } : task
      ),
    })),

  addProject: (project) =>
    set((state) => {
      const newProject = { ...project, id: uid() };
      return {
        projects: [newProject, ...state.projects],
        selectedProject: state.selectedProject ?? newProject.id,
      };
    }),

  updateProject: (projectId, updates) =>
    set((state) => ({
      projects: state.projects.map((project) =>
        project.id === projectId ? { ...project, ...updates } : project
      ),
    })),

  addNotification: (item) =>
    set((state) => ({
      notifications: [
        {
          ...item,
          id: uid(),
          timestamp: new Date().toISOString(),
          read: false,
        },
        ...state.notifications,
      ],
    })),

  markNotificationsRead: () =>
    set((state) => ({
      notifications: state.notifications.map((item) => ({
        ...item,
        read: true,
      })),
    })),

  setActiveTranscript: (transcriptId) => set({ activeTranscriptId: transcriptId }),

  updateTranscript: (transcriptId, updates) =>
    set((state) => ({
      transcripts: state.transcripts.map((transcript) =>
        transcript.id === transcriptId ? { ...transcript, ...updates } : transcript
      ),
    })),

  startProcessing: (projectId, content) =>
    set({
      pendingTranscript: { projectId, content },
      processingState: {
        isProcessing: true,
        currentStep: 0,
        cancelled: false,
      },
    }),

  advanceProcessing: () =>
    set((state) => {
      if (!state.processingState.isProcessing) {
        return state;
      }

      const nextStep = Math.min(
        state.processingState.currentStep + 1,
        PROCESSING_STEPS.length - 1
      );

      return {
        processingState: {
          ...state.processingState,
          currentStep: nextStep,
        },
      };
    }),

  cancelProcessing: () =>
    set((state) => ({
      processingState: {
        ...state.processingState,
        isProcessing: false,
        cancelled: true,
      },
      pendingTranscript: null,
    })),

  resetProcessing: () =>
    set({
      processingState: initialProcessing,
      pendingTranscript: null,
    }),

  completeProcessing: () => {
    const { pendingTranscript, user, addNotification } = get();

    if (!pendingTranscript) {
      set({ processingState: initialProcessing });
      return;
    }

    const transcriptId = uid();
    const chunks = splitTranscript(pendingTranscript.content);
    const fallbackItems = [
      "Review transcript highlights with design team",
      "Assign owners for top action items",
      "Confirm delivery timeline in next stand-up",
    ];
    const actionLines = chunks.length > 0 ? chunks : fallbackItems;

    const generatedTasks: Task[] = actionLines.map((line, index) => ({
      id: uid(),
      projectId: pendingTranscript.projectId,
      title: line.length > 52 ? `${line.slice(0, 52)}...` : line,
      description: `Derived from transcript insight: ${line}`,
      deadline: dayShift(index + 1),
      assigneeIds: [mockUsers[(index % (mockUsers.length - 1)) + 1].id],
      transcriptReference: transcriptId,
      status: statusFromIndex(index),
    }));

    const summarySource = pendingTranscript.content.trim();
    const summary =
      summarySource.length > 180
        ? `${summarySource.slice(0, 180)}...`
        : summarySource || "Meeting summary generated from transcript.";

    const transcript: Transcript = {
      id: transcriptId,
      projectId: pendingTranscript.projectId,
      content: pendingTranscript.content,
      summary,
      createdAt: new Date().toISOString(),
      actionItemIds: generatedTasks.map((task) => task.id),
    };

    set((state) => ({
      transcripts: [transcript, ...state.transcripts],
      tasks: [...generatedTasks, ...state.tasks],
      activeTranscriptId: transcriptId,
      pendingTranscript: null,
      processingState: {
        isProcessing: false,
        currentStep: PROCESSING_STEPS.length - 1,
        cancelled: false,
      },
    }));

    addNotification({
      message: `Action items generated from transcript for ${pendingTranscript.projectId}.`,
      type: "success",
    });

    if (user) {
      addNotification({
        message: `${user.name} completed AI action item extraction.`,
        type: "info",
      });
    }
  },
}));

export { mockUsers };
