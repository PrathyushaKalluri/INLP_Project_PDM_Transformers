import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { User } from "@/types";

interface AvatarGroupProps {
  users: User[];
  max?: number;
}

export function AvatarGroup({ users, max = 3 }: AvatarGroupProps) {
  const visible = users.slice(0, max);
  const remaining = users.length - visible.length;

  return (
    <div className="flex -space-x-2">
      {visible.map((user) => (
        <Avatar key={user.id} className="h-7 w-7 border border-card">
          <AvatarFallback>{user.avatar}</AvatarFallback>
        </Avatar>
      ))}
      {remaining > 0 ? (
        <div className="flex h-7 w-7 items-center justify-center rounded-full border border-card bg-muted text-xs text-text-secondary">
          +{remaining}
        </div>
      ) : null}
    </div>
  );
}
