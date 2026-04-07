"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { KanbanColumn } from "@/components/kanban/kanban-column";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { getProjects } from "@/lib/api/projects.api";
import { queryKeys } from "@/lib/api/query-keys";
import { getTasks } from "@/lib/api/tasks.api";
import { buildUserDirectory } from "@/lib/api/user-directory";
import { applyTaskFilters } from "@/lib/tasks";
import { getErrorMessage } from "@/lib/utils";
import { useAppStore } from "@/store/useAppStore";

export default function KanbanPage() {
  const user = useAppStore((state) => state.user);
  const selectedProject = useAppStore((state) => state.selectedProject);
  const setSelectedProject = useAppStore((state) => state.setSelectedProject);
  const filters = useAppStore((state) => state.filters);

  const [loading, setLoading] = useState(true);

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: getProjects,
  });

  const tasksQuery = useQuery({
    queryKey: selectedProject ? queryKeys.tasks(selectedProject) : ["tasks", "none"],
    queryFn: () => getTasks(selectedProject ?? ""),
    enabled: Boolean(selectedProject),
  });

  const projects = useMemo(() => projectsQuery.data ?? [], [projectsQuery.data]);
  const tasks = useMemo(() => tasksQuery.data ?? [], [tasksQuery.data]);

  useEffect(() => {
    const timeout = setTimeout(() => setLoading(false), 450);
    return () => clearTimeout(timeout);
  }, [selectedProject]);

  useEffect(() => {
    if (!selectedProject && projects.length > 0) {
      setSelectedProject(projects[0].id);
    }
  }, [selectedProject, projects, setSelectedProject]);

  const currentProject = projects.find((project) => project.id === selectedProject);

  const userDirectory = useMemo(() => {
    const ids: string[] = [];
    projects.forEach((project) => {
      ids.push(...project.participants);
    });
    tasks.forEach((task) => {
      ids.push(...task.assigneeIds);
    });

    return buildUserDirectory(user, ids);
  }, [user, projects, tasks]);

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

  if (projectsQuery.isError || tasksQuery.isError) {
    return (
      <EmptyState
        title="Failed to load board"
        description={getErrorMessage(projectsQuery.error ?? tasksQuery.error)}
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
            usersMap={userDirectory}
            loading={loading || projectsQuery.isLoading || tasksQuery.isLoading}
          />
          <KanbanColumn
            title="Work in Progress"
            status="in-progress"
            tasks={inProgress}
            projectId={selectedProject}
            usersMap={userDirectory}
            loading={loading || projectsQuery.isLoading || tasksQuery.isLoading}
          />
          <KanbanColumn
            title="Completed"
            status="completed"
            tasks={completed}
            projectId={selectedProject}
            usersMap={userDirectory}
            loading={loading || projectsQuery.isLoading || tasksQuery.isLoading}
          />
        </div>
      )}
    </div>
  );
}
