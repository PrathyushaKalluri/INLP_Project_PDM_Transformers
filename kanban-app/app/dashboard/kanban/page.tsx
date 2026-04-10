"use client";

import { useEffect, useMemo, useState } from "react";

import { KanbanColumn } from "@/components/kanban/kanban-column";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { applyTaskFilters } from "@/lib/tasks";
import { listProjects } from "@/lib/projects";
import { listTasks } from "@/lib/tasks";
import { useAppStore } from "@/store/useAppStore";

export default function KanbanPage() {
  const user = useAppStore((state) => state.user);
  const selectedProject = useAppStore((state) => state.selectedProject);
  const projects = useAppStore((state) => state.projects);
  const tasks = useAppStore((state) => state.tasks);
  const filters = useAppStore((state) => state.filters);
  const setProjects = useAppStore((state) => state.setProjects);
  const setTasks = useAppStore((state) => state.setTasks);
  const setSelectedProject = useAppStore((state) => state.setSelectedProject);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch projects on mount
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setError(null);
        const result = await listProjects();
        setProjects(result.projects);

        // Auto-select first project if none selected
        if (result.projects.length > 0 && !selectedProject) {
          setSelectedProject(result.projects[0].id);
        }
      } catch (err) {
        console.error("Failed to fetch projects:", err);
        setError("Failed to load projects");
      }
    };

    fetchProjects();
  }, []);

  // Fetch tasks when selected project changes
  useEffect(() => {
    const fetchTasks = async () => {
      if (!selectedProject) return;

      try {
        setLoading(true);
        setError(null);
        const result = await listTasks({ projectId: selectedProject });
        setTasks(result.tasks);
      } catch (err) {
        console.error("Failed to fetch tasks:", err);
        setError("Failed to load tasks");
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, [selectedProject, setTasks]);

  const currentProject = projects.find(
    (project) => project.id === selectedProject,
  );

  const filteredTasks = useMemo(() => {
    if (!selectedProject) {
      return [];
    }
    const scoped = tasks.filter((task) => task.projectId === selectedProject);
    return applyTaskFilters(scoped, filters, user?.id ?? null);
  }, [tasks, selectedProject, filters, user?.id]);

  if (projects.length === 0) {
    return (
      <EmptyState
        title="No projects"
        description="Create a project from the sidebar to start organizing tasks."
      />
    );
  }

  if (!selectedProject || !currentProject) {
    return (
      <EmptyState
        title="No project selected"
        description="Pick a project from the sidebar to view the board."
      />
    );
  }

  const todo = filteredTasks.filter((task) => task.status === "todo");
  const inProgress = filteredTasks.filter(
    (task) => task.status === "in-progress",
  );
  const completed = filteredTasks.filter((task) => task.status === "completed");

  const hasNoTasks = !loading && filteredTasks.length === 0;

  // Show error state
  if (error) {
    return <EmptyState title="Error loading tasks" description={error} />;
  }

  return (
    <div className="space-y-4">
      <SectionHeading
        title="Kanban Board"
        subtitle={currentProject?.description ?? ""}
      />

      {hasNoTasks ? (
        <EmptyState
          title="No tasks found"
          description="No tasks match your current filters. Try resetting filter settings or add a new task."
        />
      ) : (
        <div className="grid items-start gap-4 xl:grid-cols-3">
          <KanbanColumn
            title="To-Do"
            status="todo"
            tasks={todo}
            projectId={selectedProject}
            loading={loading}
          />
          <KanbanColumn
            title="Work in Progress"
            status="in-progress"
            tasks={inProgress}
            projectId={selectedProject}
            loading={loading}
          />
          <KanbanColumn
            title="Completed"
            status="completed"
            tasks={completed}
            projectId={selectedProject}
            loading={loading}
          />
        </div>
      )}
    </div>
  );
}
