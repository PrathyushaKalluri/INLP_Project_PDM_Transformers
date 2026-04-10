"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { listWorkspacesApi } from "@/lib/teams";
import { getAccessToken } from "@/lib/api";

export default function DebugPage() {
  const [debug, setDebug] = useState<string[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<any[]>([]);

  useEffect(() => {
    const t = getAccessToken();
    setToken(t ? "t: " + t.substring(0, 20) + "..." : "NO TOKEN");
  }, []);

  const addDebug = (msg: string) => {
    setDebug((prev) => [...prev, `${new Date().toLocaleTimeString()}: ${msg}`]);
  };

  const testFetch = async () => {
    try {
      addDebug("Starting workspace fetch...");
      const ws = await listWorkspacesApi();
      addDebug(`Success! Got ${ws.length} workspaces`);
      setWorkspaces(ws);
      ws.forEach((w: any) => {
        addDebug(`  - ${w.name} (${w.id})`);
      });
    } catch (err) {
      addDebug(`Error: ${err instanceof Error ? err.message : String(err)}`);
      console.error("Full error:", err);
    }
  };

  return (
    <div className="p-8 space-y-4">
      <h1 className="text-2xl font-bold">Team Modal Debug</h1>

      <div className="border p-4 rounded space-y-2">
        <Label>Auth Token Status</Label>
        <div className="font-mono text-sm p-2 bg-muted rounded">{token}</div>
      </div>

      <Button onClick={testFetch}>Test Workspace Fetch</Button>

      <div className="border p-4 rounded">
        <Label>Debug Log</Label>
        <div className="font-mono text-xs space-y-1 max-h-96 overflow-y-auto bg-muted p-2 rounded mt-2">
          {debug.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
          {debug.length === 0 && (
            <div className="text-text-secondary">No logs yet...</div>
          )}
        </div>
      </div>

      {workspaces.length > 0 && (
        <div className="border p-4 rounded">
          <Label>Workspaces Loaded</Label>
          <div className="space-y-2 mt-2">
            {workspaces.map((ws: any) => (
              <div key={ws.id} className="p-2 bg-muted rounded">
                <div className="font-medium">{ws.name}</div>
                <div className="text-xs text-text-secondary">{ws.id}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
