"use client";

import { useMemo } from "react";

import { FilterPanel } from "@/components/tasks/filter-panel";
import { BrandLogo } from "@/components/shared/BrandLogo";
import { NotificationsPanel } from "@/components/layout/notifications-panel";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useAppStore } from "@/store/useAppStore";

export function Topbar() {
  const projects = useAppStore((state) => state.projects);
  const selectedProject = useAppStore((state) => state.selectedProject);
  const setSelectedProject = useAppStore((state) => state.setSelectedProject);
  const filters = useAppStore((state) => state.filters);
  const setFilters = useAppStore((state) => state.setFilters);

  const hasProjects = projects.length > 0;

  const projectLabel = useMemo(
    () =>
      projects.find((project) => project.id === selectedProject)?.name ??
      "Select project",
    [projects, selectedProject],
  );

  return (
    <header className="kbn-fade-up kbn-delay-1 flex flex-wrap items-center justify-end gap-3 rounded-xl border border-border bg-card p-3 shadow-sm">
      <div className="min-w-56">
        {hasProjects ? (
          <Select
            value={selectedProject ?? undefined}
            onValueChange={setSelectedProject}
          >
            <SelectTrigger>
              <SelectValue placeholder={projectLabel} />
            </SelectTrigger>
            <SelectContent>
              {projects.map((project) => (
                <SelectItem key={project.id} value={project.id}>
                  {project.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <div className="rounded-xl border border-border bg-card px-3 py-2 text-sm text-text-secondary">
            No projects
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 rounded-xl border border-border px-3 py-2">
        <Label htmlFor="my-task-toggle" className="text-sm text-text-secondary">
          My Tasks
        </Label>
        <Switch
          id="my-task-toggle"
          checked={filters.onlyMine}
          onCheckedChange={(checked) => setFilters({ onlyMine: checked })}
        />
      </div>

      <FilterPanel />

      <NotificationsPanel />

      <BrandLogo
        variant="full"
        className="hidden md:block h-8 w-auto px-2 py-1"
      />
      <BrandLogo
        variant="icon"
        className="block md:hidden h-8 w-auto px-2 py-1"
      />
    </header>
  );
}
