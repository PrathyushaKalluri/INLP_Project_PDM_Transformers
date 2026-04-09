"use client";

import { useState } from "react";

import { ProjectModal } from "@/components/layout/project-modal";
import { NotificationToasts } from "@/components/layout/notification-toasts";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

interface DashboardShellProps {
  children: React.ReactNode;
}

export function DashboardShell({ children }: DashboardShellProps) {
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);

  const openAddProject = () => {
    setEditingProjectId(null);
    setProjectModalOpen(true);
  };

  const openEditProject = (projectId: string) => {
    setEditingProjectId(projectId);
    setProjectModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-background p-4 md:p-6">
      <div className="grid min-h-[calc(100vh-2rem)] items-start gap-4 md:min-h-[calc(100vh-3rem)] md:grid-cols-[18rem_minmax(0,1fr)] md:gap-5">
        <Sidebar onAddProject={openAddProject} onEditProject={openEditProject} />

        <div className="flex min-h-full flex-col gap-4">
          <Topbar />
          <main className="flex-1 pb-4">{children}</main>
        </div>
      </div>

      <ProjectModal
        open={projectModalOpen}
        onOpenChange={setProjectModalOpen}
        projectId={editingProjectId}
      />
      <NotificationToasts />
    </div>
  );
}
