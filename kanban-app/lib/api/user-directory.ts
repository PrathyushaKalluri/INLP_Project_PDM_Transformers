import type { User } from "@/types";

const toFallbackUser = (id: string): User => {
  const label = `User ${id.slice(0, 4).toUpperCase()}`;
  const avatar = label
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return {
    id,
    name: label,
    email: `${id}@placeholder.local`,
    role: "member",
    avatar,
  };
};

export const buildUserDirectory = (user: User | null, ids: string[]) => {
  const unique = new Set(ids);
  if (user) {
    unique.add(user.id);
  }

  const map = new Map<string, User>();
  unique.forEach((id) => {
    if (user && user.id === id) {
      map.set(id, user);
    } else {
      map.set(id, toFallbackUser(id));
    }
  });

  return map;
};
