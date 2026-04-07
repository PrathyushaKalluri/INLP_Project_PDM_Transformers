"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Download,
  FileText,
  FolderKanban,
  LogOut,
  MoreHorizontal,
  Plus,
  Settings,
  Upload,
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
import { logout } from "@/lib/api/auth.api";
import { getProjects } from "@/lib/api/projects.api";
import { queryKeys } from "@/lib/api/query-keys";
import { getTasks } from "@/lib/api/tasks.api";
import { getTranscripts } from "@/lib/api/transcripts.api";
import { getErrorMessage } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";
import { useAppStore } from "@/store/useAppStore";

interface SidebarProps {
  onAddProject: () => void;
  onEditProject: (projectId: string) => void;
}

export function Sidebar({ onAddProject, onEditProject }: SidebarProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const user = useAppStore((state) => state.user);
  const selectedProject = useAppStore((state) => state.selectedProject);
  const setSelectedProject = useAppStore((state) => state.setSelectedProject);
  const logoutLocal = useAppStore((state) => state.logoutLocal);

  const router = useRouter();
  const pathname = usePathname();

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: getProjects,
  });

  const projects = projectsQuery.data ?? [];

  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      logoutLocal();
      queryClient.clear();
      router.replace("/auth/login");
    },
    onError: (error) => {
      toast({
        title: "Logout failed",
        description: getErrorMessage(error),
      });
      logoutLocal();
      queryClient.clear();
      router.replace("/auth/login");
    },
  });

  const exportWorkspace = async () => {
    try {
      const [tasksByProject, transcriptsByProject] = await Promise.all([
        Promise.all(projects.map((project) => getTasks(project.id))),
        Promise.all(projects.map((project) => getTranscripts(project.id))),
      ]);

      const payload = {
        exportedAt: new Date().toISOString(),
        projects,
        tasks: tasksByProject.flat(),
        transcripts: transcriptsByProject.flat(),
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
    } catch (error) {
      toast({
        title: "Export failed",
        description: getErrorMessage(error),
      });
    }
  };

  const handleLogout = async () => {
    await logoutMutation.mutateAsync();
  };

  const isManager = user?.role === "manager";

  return (
    <aside className="flex h-full w-full flex-col rounded-xl border border-border bg-card p-4 shadow-sm md:sticky md:top-6 md:h-[calc(100vh-3rem)] md:w-72">
      <div className="flex items-center gap-3 rounded-xl bg-muted/60 p-3">
        <Avatar>
          <AvatarFallback>{user?.avatar ?? "NA"}</AvatarFallback>
        </Avatar>
        <div>
          <p className="text-sm font-medium text-text-primary">{user?.name ?? "Guest"}</p>
          <p className="text-xs text-text-secondary">{user?.role ?? "visitor"}</p>
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
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => onEditProject(project.id)}>
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

      <div className="space-y-1">
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
          onClick={() => void exportWorkspace()}
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
