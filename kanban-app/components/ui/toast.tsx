"use client";

import * as React from "react";
import * as ToastPrimitives from "@radix-ui/react-toast";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

function ToastProvider({ ...props }: React.ComponentProps<typeof ToastPrimitives.Provider>) {
  return <ToastPrimitives.Provider {...props} />;
}

function ToastViewport({
  className,
  ...props
}: React.ComponentProps<typeof ToastPrimitives.Viewport>) {
  return (
    <ToastPrimitives.Viewport
      className={cn(
        "fixed right-0 bottom-0 z-[100] flex max-h-screen w-full flex-col-reverse gap-2 p-4 sm:right-4 sm:top-4 sm:bottom-auto sm:w-96",
        className
      )}
      {...props}
    />
  );
}

function Toast({ className, ...props }: React.ComponentProps<typeof ToastPrimitives.Root>) {
  return (
    <ToastPrimitives.Root
      data-slot="toast"
      className={cn(
        "group pointer-events-auto relative flex w-full items-start gap-2 overflow-hidden rounded-xl border border-border bg-card p-4 shadow-sm",
        className
      )}
      {...props}
    />
  );
}

function ToastTitle({
  className,
  ...props
}: React.ComponentProps<typeof ToastPrimitives.Title>) {
  return <ToastPrimitives.Title className={cn("text-sm font-medium", className)} {...props} />;
}

function ToastDescription({
  className,
  ...props
}: React.ComponentProps<typeof ToastPrimitives.Description>) {
  return (
    <ToastPrimitives.Description
      className={cn("text-sm text-text-secondary", className)}
      {...props}
    />
  );
}

function ToastClose({
  className,
  ...props
}: React.ComponentProps<typeof ToastPrimitives.Close>) {
  return (
    <ToastPrimitives.Close
      className={cn(
        "absolute top-2 right-2 rounded-md p-1 text-text-secondary hover:text-text-primary",
        className
      )}
      {...props}
    >
      <X className="h-4 w-4" />
    </ToastPrimitives.Close>
  );
}

function ToastAction({
  className,
  ...props
}: React.ComponentProps<typeof ToastPrimitives.Action>) {
  return (
    <ToastPrimitives.Action
      className={cn(
        "inline-flex h-8 shrink-0 items-center justify-center rounded-lg border border-border px-3 text-sm font-medium hover:bg-muted",
        className
      )}
      {...props}
    />
  );
}

export {
  ToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastClose,
  ToastAction,
};
