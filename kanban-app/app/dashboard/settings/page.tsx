"use client";

import { SectionHeading } from "@/components/shared/section-heading";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useAppStore } from "@/store/useAppStore";

export default function SettingsPage() {
  const themeMode = useAppStore((state) => state.themeMode);
  const setThemeMode = useAppStore((state) => state.setThemeMode);

  const darkModeEnabled = themeMode === "dark";

  return (
    <div className="space-y-4">
      <SectionHeading
        title="Settings"
        subtitle="Adjust workspace behavior and appearance preferences."
      />

      <Card className="kbn-fade-up kbn-delay-1 transition-colors duration-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl font-medium">
            Theme
            <Badge variant="primary">Appearance</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-muted/45 px-4 py-3">
            <div className="space-y-1">
              <Label htmlFor="theme-mode-toggle" className="text-sm text-text-primary">
                Dark mode
              </Label>
              <p className="text-xs text-text-secondary">
                Uses warm accent colors in both light and dark themes.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">Light</span>
              <Switch
                id="theme-mode-toggle"
                checked={darkModeEnabled}
                className="transition-transform duration-200 active:scale-95"
                onCheckedChange={(checked) =>
                  setThemeMode(checked ? "dark" : "light")
                }
              />
              <span className="text-xs text-text-secondary">Dark</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
