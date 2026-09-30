"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const value = localStorage.getItem("shodh-theme") === "dark";
    setDark(value);
    document.documentElement.classList.toggle("dark", value);
  }, []);
  function toggle() {
    const next = !dark;
    setDark(next);
    localStorage.setItem("shodh-theme", next ? "dark" : "light");
    document.documentElement.classList.toggle("dark", next);
  }
  return <button onClick={toggle} aria-label="Toggle dark mode" className="rounded-md p-2 text-foreground/45 hover:bg-foreground/[.05]">{dark ? <Sun size={15}/> : <Moon size={15}/>}</button>;
}
