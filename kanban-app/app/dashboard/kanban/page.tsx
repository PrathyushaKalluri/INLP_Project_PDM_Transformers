"use client";

import { useEffect, useMemo, useState } from "react";

import { KanbanColumn } from "@/components/kanban/kanban-column";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { applyTaskFilters } from "@/lib/tasks";
import { listProjects } from "@/lib/projects";
import { listTasks } from "@/lib/tasks";
import { listTeamMembersApi } from "@/lib/teams";
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
  const [assigneeNamesById, setAssigneeNamesById] = useState<
    Record<string, string>
  >({});

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

  const currentProject = projects.find(
    (project) => project.id === selectedProject,
  );

  // Fetch tasks and team members together when the active project changes.
  useEffect(() => {
    let cancelled = false;

    const fetchProjectData = async () => {
      if (!selectedProject || !currentProject) return;

      try {
        setLoading(true);
        setError(null);

        const [taskResult, members] = await Promise.all([
          listTasks({ projectId: selectedProject }),
          currentProject.teamId
            ? listTeamMembersApi(currentProject.teamId)
            : Promise.resolve([]),
        ]);

        if (cancelled) return;

        setTasks(taskResult.tasks);

        const map = members.reduce<Record<string, string>>((acc, member) => {
          acc[member.user_id] = member.full_name;
          return acc;
        }, {});
        setAssigneeNamesById(map);
      } catch (err) {
        console.error("Failed to fetch tasks:", err);
        setError("Failed to load tasks");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchProjectData();

    return () => {
      cancelled = true;
    };
  }, [selectedProject, currentProject, setTasks]);

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

  const { todo, inProgress, completed } = useMemo(() => {
    return filteredTasks.reduce(
      (acc, task) => {
        if (task.status === "todo") {
          acc.todo.push(task);
        } else if (task.status === "in-progress") {
          acc.inProgress.push(task);
        } else {
          acc.completed.push(task);
        }
        return acc;
      },
      {
        todo: [] as typeof filteredTasks,
        inProgress: [] as typeof filteredTasks,
        completed: [] as typeof filteredTasks,
      },
    );
  }, [filteredTasks]);

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
            assigneeNamesById={assigneeNamesById}
            loading={loading}
          />
          <KanbanColumn
            title="Work in Progress"
            status="in-progress"
            tasks={inProgress}
            projectId={selectedProject}
            assigneeNamesById={assigneeNamesById}
            loading={loading}
          />
          <KanbanColumn
            title="Completed"
            status="completed"
            tasks={completed}
            projectId={selectedProject}
            assigneeNamesById={assigneeNamesById}
            loading={loading}
          />
        </div>
      )}
    </div>
  );
}
