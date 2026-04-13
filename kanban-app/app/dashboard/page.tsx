"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/store/useAppStore";
import { listProjects } from "@/lib/projects";
import { EmptyState } from "@/components/shared/empty-state";

export default function DashboardPage() {
  const router = useRouter();
  const projects = useAppStore((state) => state.projects);
  const setProjects = useAppStore((state) => state.setProjects);
  const setSelectedProject = useAppStore((state) => state.setSelectedProject);

  useEffect(() => {
    // If projects already loaded, redirect to first one
    if (projects.length > 0) {
      setSelectedProject(projects[0].id);
      router.replace(`/dashboard/kanban`);
      return;
    }

    // Otherwise fetch projects
    const fetchProjects = async () => {
      try {
        const result = await listProjects();
        setProjects(result.projects);

        if (result.projects.length > 0) {
          setSelectedProject(result.projects[0].id);
          router.replace(`/dashboard/kanban`);
        }
      } catch (error) {
        console.error("Failed to load projects:", error);
      }
    };

    fetchProjects();
  }, [projects, router, setProjects, setSelectedProject]);

  // Loading state
  return (
    <EmptyState
      title="Loading projects..."
      description="Please wait while we fetch your projects."
    />
  );
}
