"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

type BrandLogoProps = {
  variant?: "full" | "icon";
  className?: string;
};

const logoByVariant = {
  full: {
    src: "/assets/logo/logo-full.svg",
    alt: "Brand logo",
    width: 287,
    height: 56,
  },
  icon: {
    src: "/assets/logo/logo-icon.svg",
    alt: "Brand icon",
    width: 49,
    height: 48,
  },
} as const;

export function BrandLogo({ variant = "full", className }: BrandLogoProps) {
  const baseLogo = logoByVariant[variant];
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    const syncTheme = () => {
      setIsDarkTheme(root.getAttribute("data-theme") === "dark");
    };

    syncTheme();

    const observer = new MutationObserver(syncTheme);
    observer.observe(root, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    return () => observer.disconnect();
  }, []);

  const logo =
    variant === "full" && isDarkTheme
      ? { ...baseLogo, src: "/assets/logo/logo-full-light.svg" }
      : baseLogo;

  return (
    <Image
      src={logo.src}
      alt={logo.alt}
      width={logo.width}
      height={logo.height}
      priority
      className={cn("h-8 w-auto object-contain", className)}
    />
  );
}
