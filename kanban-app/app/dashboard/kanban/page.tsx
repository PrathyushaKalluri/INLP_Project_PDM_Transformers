"use client";

import { useEffect, useMemo, useState } from "react";

import { KanbanColumn } from "@/components/kanban/kanban-column";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { applyTaskFilters } from "@/lib/tasks";
import { useAppStore } from "@/store/useAppStore";

export default function KanbanPage() {
  const user = useAppStore((state) => state.user);
  const selectedProject = useAppStore((state) => state.selectedProject);
  const projects = useAppStore((state) => state.projects);
  const tasks = useAppStore((state) => state.tasks);
  const filters = useAppStore((state) => state.filters);

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timeout = setTimeout(() => setLoading(false), 450);
    return () => clearTimeout(timeout);
  }, [selectedProject]);

  const currentProject = projects.find((project) => project.id === selectedProject);

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
  const inProgress = filteredTasks.filter((task) => task.status === "in-progress");
  const completed = filteredTasks.filter((task) => task.status === "completed");

  const hasNoTasks = !loading && filteredTasks.length === 0;

  return (
    <div className="space-y-4">
      <SectionHeading
        title="Kanban Board"
        subtitle={currentProject.description}
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
