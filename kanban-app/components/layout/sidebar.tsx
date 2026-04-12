"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Download,
  FileText,
  FolderKanban,
  LogOut,
  MoreHorizontal,
  Plus,
  Settings,
  Upload,
  Users,
} from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useAppStore } from "@/store/useAppStore";

interface SidebarProps {
  onAddProject: () => void;
  onEditProject: (projectId: string) => void;
  onCreateTeam: () => void;
}

export function Sidebar({
  onAddProject,
  onEditProject,
  onCreateTeam,
}: SidebarProps) {
  const user = useAppStore((state) => state.user);
  const projects = useAppStore((state) => state.projects);
  const selectedProject = useAppStore((state) => state.selectedProject);
  const setSelectedProject = useAppStore((state) => state.setSelectedProject);
  const tasks = useAppStore((state) => state.tasks);
  const transcripts = useAppStore((state) => state.transcripts);
  const logout = useAppStore((state) => state.logout);

  const router = useRouter();
  const pathname = usePathname();

  const exportWorkspace = () => {
    const payload = {
      exportedAt: new Date().toISOString(),
      projects,
      tasks,
      transcripts,
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "workspace-export.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleLogout = () => {
    logout();
    router.replace("/auth/login");
  };

  const isManager = user?.role === "manager";

  return (
    <aside className="flex w-full flex-col overflow-hidden rounded-xl border border-border bg-card p-4 shadow-sm md:sticky md:top-6 md:h-[calc(100vh-3rem)] md:w-72">
      <div className="flex items-center gap-3 rounded-xl bg-muted/60 p-3">
        <Avatar>
          <AvatarFallback>{user?.avatar ?? "NA"}</AvatarFallback>
        </Avatar>
        <div>
          <p className="text-sm font-medium text-text-primary">
            {user?.name ?? "Guest"}
          </p>
          <p className="text-xs text-text-secondary">
            {user?.role ?? "visitor"}
          </p>
        </div>
      </div>

      <Separator className="my-4" />

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-text-primary">Teams</h3>
          <Button
            variant="ghost"
            size="icon"
            onClick={onCreateTeam}
            title="Create team"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        <div className="rounded-xl border border-dashed border-border p-3 text-xs text-text-secondary">
          Teams management available from project creation menu
        </div>
      </div>

      <Separator className="my-4" />

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-text-primary">Kanban</h3>
          {isManager ? (
            <Button variant="ghost" size="icon" onClick={onAddProject}>
              <Plus className="h-4 w-4" />
            </Button>
          ) : null}
        </div>

        {projects.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border p-3 text-xs text-text-secondary">
            No projects available.
          </div>
        ) : (
          <ScrollArea className="h-52">
            <div className="space-y-1 pr-3">
              {projects.map((project) => {
                const active = selectedProject === project.id;
                return (
                  <div
                    key={project.id}
                    className={`flex items-center gap-1 rounded-xl border px-2 py-1 ${
                      active
                        ? "border-primary bg-primary/20"
                        : "border-transparent hover:border-border"
                    }`}
                  >
                    <button
                      type="button"
                      className="flex flex-1 items-center gap-2 rounded-lg px-1 py-1 text-left"
                      onClick={() => {
                        setSelectedProject(project.id);
                        router.push("/dashboard/kanban");
                      }}
                    >
                      <FolderKanban className="h-4 w-4 text-text-secondary" />
                      <span className="truncate text-sm text-text-primary">
                        {project.name}
                      </span>
                    </button>

                    {isManager ? (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => onEditProject(project.id)}
                          >
                            Edit project
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        )}
      </div>

      <Separator className="my-4" />

      <div className="min-h-0 flex-1 space-y-1 overflow-y-auto pr-1">
        <Link
          href="/dashboard/teams"
          className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${
            pathname === "/dashboard/teams"
              ? "bg-primary/20 text-text-primary"
              : "text-text-secondary hover:bg-muted"
          }`}
        >
          <Users className="h-4 w-4" />
          Teams Management
        </Link>

        <Link
          href="/dashboard/publish"
          className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${
            pathname === "/dashboard/publish"
              ? "bg-primary/20 text-text-primary"
              : "text-text-secondary hover:bg-muted"
          }`}
        >
          <FileText className="h-4 w-4" />
          Meeting Summaries
        </Link>

        <Link
          href="/dashboard/settings"
          className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${
            pathname === "/dashboard/settings"
              ? "bg-primary/20 text-text-primary"
              : "text-text-secondary hover:bg-muted"
          }`}
        >
          <Settings className="h-4 w-4" />
          Settings
        </Link>

        {isManager ? (
          <button
            type="button"
            onClick={onAddProject}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-text-secondary hover:bg-muted"
          >
            <Plus className="h-4 w-4" />
            Add Project
          </button>
        ) : null}

        <Link
          href="/dashboard/upload"
          className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${
            pathname === "/dashboard/upload"
              ? "bg-primary/20 text-text-primary"
              : "text-text-secondary hover:bg-muted"
          }`}
        >
          <Upload className="h-4 w-4" />
          Upload Transcript
        </Link>

        <button
          type="button"
          onClick={exportWorkspace}
          className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-text-secondary hover:bg-muted"
        >
          <Download className="h-4 w-4" />
          Export
        </button>

        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-danger hover:bg-danger/10"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </div>
    </aside>
  );
}
