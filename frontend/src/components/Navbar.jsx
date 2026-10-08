import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function titleFromPath(pathname) {
  const segment = pathname.split("/").filter(Boolean)[0] ?? "dashboard";
  return segment.charAt(0).toUpperCase() + segment.slice(1);
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

function CollapseIcon({ collapsed }) {
  return collapsed ? (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
      <path d="m10 6 6 6-6 6" />
      <path d="M4 4v16" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
      <path d="m14 6-6 6 6 6" />
      <path d="M20 4v16" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
      <path d="M15 17h5l-1.4-1.4a2 2 0 0 1-.6-1.4V11a6 6 0 1 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5" />
      <path d="M9 17a3 3 0 0 0 6 0" />
    </svg>
  );
}

export default function Navbar({ onToggleSidebar, onToggleCollapse, isSidebarOpen, isSidebarCollapsed }) {
  const { currentUser, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pageTitle = titleFromPath(location.pathname);

  const userName = useMemo(
    () => currentUser?.name || currentUser?.full_name || currentUser?.email || "Authenticated User",
    [currentUser]
  );

  const userRole = useMemo(() => {
    const rawRole = currentUser?.role || "Dispatcher";
    return String(rawRole).replace(/_/g, " ");
  }, [currentUser]);

  return (
    <header className="sticky top-0 z-30 border-b border-slate-800/90 bg-slate-900/90 backdrop-blur-xl">
      <div className="flex h-16 items-center justify-between px-4 sm:h-20 sm:px-6 lg:px-8">
      <div className="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 text-slate-200 transition hover:bg-slate-800 md:hidden"
          aria-label="Open menu"
          aria-expanded={isSidebarOpen}
        >
          <MenuIcon />
        </button>

        <button
          type="button"
          onClick={onToggleCollapse}
          className="hidden h-9 w-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 text-slate-200 transition hover:bg-slate-800 md:inline-flex"
          aria-label="Toggle sidebar"
        >
          <CollapseIcon collapsed={isSidebarCollapsed} />
        </button>

        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-teal-300">Operations</p>
          <h1 className="text-base font-semibold text-white sm:text-lg">{pageTitle}</h1>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          className="relative inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 text-slate-200 transition hover:bg-slate-800"
          aria-label="Notifications"
        >
          <BellIcon />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-teal-400" aria-hidden="true" />
        </button>

        <div className="hidden text-right sm:block">
          <p className="text-sm font-medium text-slate-100">{userName}</p>
          <p className="text-xs capitalize text-slate-400">{userRole}</p>
        </div>

        <button
          type="button"
          onClick={logout}
          className="hidden rounded-lg border border-slate-700 px-3 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-800 sm:inline-flex"
        >
          Logout
        </button>

        <button
          type="button"
          onClick={() => setMobileMenuOpen((prev) => !prev)}
          className="inline-flex h-9 items-center rounded-lg border border-slate-700 bg-slate-900 px-2.5 text-xs font-medium text-slate-200 transition hover:bg-slate-800 sm:hidden"
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-user-menu"
        >
          Account
        </button>
      </div>
      </div>

      <div
        id="mobile-user-menu"
        className={`overflow-hidden border-t border-slate-800 bg-slate-900/95 px-4 transition-[max-height,opacity] duration-300 sm:hidden ${
          mobileMenuOpen ? "max-h-40 py-3 opacity-100" : "max-h-0 py-0 opacity-0"
        }`}
      >
        <p className="text-sm font-medium text-slate-100">{userName}</p>
        <p className="mt-0.5 text-xs capitalize text-slate-400">{userRole}</p>
        <button
          type="button"
          onClick={logout}
          className="mt-3 inline-flex w-full items-center justify-center rounded-lg border border-slate-700 px-3 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-800"
        >
          Logout
        </button>
      </div>
    </header>
  );
}
