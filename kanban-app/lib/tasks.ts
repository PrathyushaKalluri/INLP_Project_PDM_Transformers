import type { FilterState, Task } from "@/types";

const isSameDate = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() &&
  a.getMonth() === b.getMonth() &&
  a.getDate() === b.getDate();

export const getTaskUrgency = (deadline: string): "default" | "near" | "overdue" => {
  const due = new Date(deadline);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  due.setHours(0, 0, 0, 0);

  if (due < today) {
    return "overdue";
  }

  const diff = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diff <= 2) {
    return "near";
  }

  return "default";
};

export const applyTaskFilters = (
  tasks: Task[],
  filters: FilterState,
  userId: string | null
) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const filtered = tasks.filter((task) => {
    const due = new Date(task.deadline);
    due.setHours(0, 0, 0, 0);

    if (filters.onlyMine && userId && !task.assigneeIds.includes(userId)) {
      return false;
    }

    if (filters.customDate) {
      const custom = new Date(filters.customDate);
      custom.setHours(0, 0, 0, 0);
      if (!isSameDate(due, custom)) {
        return false;
      }
    }

    if (filters.deadlineFilter === "today" && !isSameDate(due, today)) {
      return false;
    }

    if (filters.deadlineFilter === "near") {
      const urgency = getTaskUrgency(task.deadline);
      if (urgency !== "near") {
        return false;
      }
    }

    if (filters.deadlineFilter === "overdue") {
      const urgency = getTaskUrgency(task.deadline);
      if (urgency !== "overdue") {
        return false;
      }
    }

    return true;
  });

  return filtered.sort((a, b) => {
    const aTime = new Date(a.deadline).getTime();
    const bTime = new Date(b.deadline).getTime();
    return filters.sortByDate === "asc" ? aTime - bTime : bTime - aTime;
  });
};
