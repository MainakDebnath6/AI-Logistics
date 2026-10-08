import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function DashboardIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" className="h-5 w-5">
      <path d="M3 13h8V3H3zM13 21h8v-8h-8zM13 11h8V3h-8zM3 21h8v-6H3z" />
    </svg>
  );
}

function DriversIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" className="h-5 w-5">
      <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="8.5" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function VehiclesIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" className="h-5 w-5">
      <path d="M3 11h18l-2-6H5z" />
      <path d="M5 11v6h14v-6" />
      <circle cx="7.5" cy="17.5" r="1.5" />
      <circle cx="16.5" cy="17.5" r="1.5" />
    </svg>
  );
}

function OrdersIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" className="h-5 w-5">
      <path d="M4 4h16v16H4z" />
      <path d="M8 8h8M8 12h8M8 16h5" />
    </svg>
  );
}

function OptimizationIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" className="h-5 w-5">
      <path d="M4 19h16" />
      <path d="M6 16 10 9l4 4 4-8" />
      <path d="M18 5h2v2" />
    </svg>
  );
}

function AnalyticsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" className="h-5 w-5">
      <path d="M3 3v18h18" />
      <path d="m7 15 4-4 3 3 5-6" />
    </svg>
  );
}

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: DashboardIcon },
  { to: "/drivers", label: "Drivers", icon: DriversIcon },
  { to: "/vehicles", label: "Vehicles", icon: VehiclesIcon },
  { to: "/orders", label: "Orders", icon: OrdersIcon },
  { to: "/optimization", label: "Optimization", icon: OptimizationIcon },
  { to: "/analytics", label: "Analytics", icon: AnalyticsIcon },
];

export default function Sidebar({ isCollapsed, isOpen, onClose }) {
  const { logout } = useAuth();

  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-black/50 transition-opacity md:hidden ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        className={`fixed left-0 top-0 z-40 h-screen border-r border-slate-800 bg-slate-950/95 shadow-xl shadow-slate-950/40 backdrop-blur transition-all duration-300 ease-out md:z-40 md:block ${
          isCollapsed ? "md:w-20" : "md:w-72"
        } ${isOpen ? "w-72 translate-x-0" : "w-72 -translate-x-full md:translate-x-0"}`}
        aria-label="Primary sidebar"
      >
        <div className="flex h-16 items-center border-b border-slate-800 px-5 sm:h-20">
          <span
            className={`text-sm font-bold uppercase tracking-[0.2em] text-teal-300 transition-all ${
              isCollapsed ? "md:w-0 md:opacity-0" : "opacity-100"
            }`}
          >
            AI Logistics
          </span>
          <span
            className={`text-sm font-bold uppercase tracking-[0.2em] text-teal-300 md:hidden ${
              isOpen ? "opacity-100" : "opacity-0"
            }`}
          >
            AI Logistics
          </span>
        </div>

        <nav className="layout-scrollbar h-[calc(100vh-5rem)] overflow-y-auto p-3 sm:h-[calc(100vh-6rem)]">
          <div className="space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              title={item.label}
              aria-label={item.label}
              className={({ isActive }) =>
                `group flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-teal-500/15 text-teal-200 ring-1 ring-teal-500/30"
                    : "text-slate-300 hover:bg-slate-800/90 hover:text-white"
                } ${isCollapsed ? "md:justify-center" : "md:justify-start"} `
              }
            >
              <span className="shrink-0">
                <item.icon />
              </span>
              <span
                className={`overflow-hidden text-nowrap transition-all duration-200 ${
                  isCollapsed ? "ml-0 w-0 opacity-0 md:hidden" : "ml-3 w-auto opacity-100"
                }`}
              >
                {item.label}
              </span>
            </NavLink>
          ))}
          </div>

          <button
            type="button"
            onClick={logout}
            title="Logout"
            aria-label="Logout"
            className={`mt-4 flex w-full items-center rounded-lg px-3 py-2.5 text-sm font-medium text-slate-300 transition-all duration-200 hover:bg-slate-800 hover:text-white ${
              isCollapsed ? "md:justify-center" : "md:justify-start"
            }`}
          >
            <span className="shrink-0">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" className="h-5 w-5">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <path d="m16 17 5-5-5-5" />
                <path d="M21 12H9" />
              </svg>
            </span>
            <span
              className={`overflow-hidden text-nowrap transition-all duration-200 ${
                isCollapsed ? "ml-0 w-0 opacity-0 md:hidden" : "ml-3 w-auto opacity-100"
              }`}
            >
              Logout
            </span>
          </button>
        </nav>
      </aside>
    </>
  );
}
