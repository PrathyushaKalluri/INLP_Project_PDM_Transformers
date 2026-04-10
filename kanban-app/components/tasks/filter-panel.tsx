"use client";

import { Filter } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { useAppStore } from "@/store/useAppStore";

export function FilterPanel() {
  const filters = useAppStore((state) => state.filters);
  const setFilters = useAppStore((state) => state.setFilters);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="secondary" size="sm">
          <Filter className="h-4 w-4" />
          Filter
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel>Task Filters</DropdownMenuLabel>
        <DropdownMenuSeparator />

        <DropdownMenuLabel className="pt-0">Sort by deadline</DropdownMenuLabel>
        <DropdownMenuRadioGroup
          value={filters.sortByDate}
          onValueChange={(value) =>
            setFilters({ sortByDate: value as "asc" | "desc" })
          }
        >
          <DropdownMenuRadioItem value="asc">
            Date ascending
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="desc">
            Date descending
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>

        <DropdownMenuSeparator />

        <DropdownMenuCheckboxItem
          checked={filters.onlyMine}
          onCheckedChange={(checked) =>
            setFilters({
              onlyMine: Boolean(checked),
              onlyUnassigned: Boolean(checked) ? false : filters.onlyUnassigned,
            })
          }
        >
          Myself only
        </DropdownMenuCheckboxItem>

        <DropdownMenuCheckboxItem
          checked={filters.onlyUnassigned}
          onCheckedChange={(checked) =>
            setFilters({
              onlyUnassigned: Boolean(checked),
              onlyMine: Boolean(checked) ? false : filters.onlyMine,
            })
          }
        >
          Unassigned only
        </DropdownMenuCheckboxItem>

        <DropdownMenuSeparator />
        <DropdownMenuLabel className="pt-0">Deadline</DropdownMenuLabel>
        <DropdownMenuRadioGroup
          value={filters.deadlineFilter}
          onValueChange={(value) =>
            setFilters({
              deadlineFilter: value as
                | "all"
                | "today"
                | "near"
                | "overdue",
            })
          }
        >
          <DropdownMenuRadioItem value="all">All</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="today">Today</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="near">Near deadline</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="overdue">Overdue</DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>

        <DropdownMenuSeparator />
        <div className="space-y-2 p-1">
          <p className="text-xs font-medium text-text-secondary">Custom date</p>
          <Input
            type="date"
            value={filters.customDate ?? ""}
            onChange={(event) =>
              setFilters({ customDate: event.target.value || null })
            }
          />
          <Button
            variant="ghost"
            size="sm"
            className="w-full"
            onClick={() => setFilters({ customDate: null })}
          >
            Clear custom date
          </Button>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
