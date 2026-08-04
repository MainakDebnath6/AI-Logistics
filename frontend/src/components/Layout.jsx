import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";

export default function Layout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const closeSidebar = () => setIsSidebarOpen(false);
  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev);
  const toggleCollapse = () => setIsSidebarCollapsed((prev) => !prev);

  useEffect(() => {
    if (!isSidebarOpen) {
      return undefined;
    }

    const { body } = document;
    const previousOverflow = body.style.overflow;
    body.style.overflow = "hidden";

    return () => {
      body.style.overflow = previousOverflow;
    };
  }, [isSidebarOpen]);

  return (
    <div className="relative flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        isOpen={isSidebarOpen}
        onClose={closeSidebar}
      />

      <div
        className={`flex min-h-screen min-w-0 flex-1 flex-col transition-[padding] duration-300 ease-out ${
          isSidebarCollapsed ? "md:pl-20" : "md:pl-72"
        }`}
      >
        <Navbar
          onToggleSidebar={toggleSidebar}
          onToggleCollapse={toggleCollapse}
          isSidebarOpen={isSidebarOpen}
          isSidebarCollapsed={isSidebarCollapsed}
        />

        <main className="flex min-h-0 flex-1">
          <div className="layout-scrollbar w-full overflow-y-auto px-4 pb-10 pt-5 sm:px-6 sm:pt-6 lg:px-8 lg:pb-12">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
