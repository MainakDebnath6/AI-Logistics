import {
  BrowserRouter,
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import Layout from "./components/Layout";
import LoadingSpinner from "./components/LoadingSpinner";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import { AuthProvider } from "./context/AuthContext";
import Analytics from "./pages/Analytics";
import Dashboard from "./pages/Dashboard";
import Drivers from "./pages/Drivers";
import Login from "./pages/Login";
import Optimization from "./pages/Optimization";
import Orders from "./pages/Orders";
import Vehicles from "./pages/Vehicles";

function AuthBootScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8 shadow-2xl shadow-slate-950/60">
        <LoadingSpinner size="lg" label="Initializing secure session..." />
      </div>
    </div>
  );
}

function NotFoundPage() {
  const location = useLocation();

  return (
    <section className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="max-w-xl rounded-2xl border border-slate-800 bg-slate-900/70 p-8 text-center shadow-xl shadow-slate-950/50">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-teal-300">Error 404</p>
        <h1 className="mt-3 text-3xl font-bold text-white">Route Not Found</h1>
        <p className="mt-3 text-sm text-slate-300">
          The route <span className="font-medium text-slate-100">{location.pathname}</span> does not exist.
        </p>
        <div className="mt-6">
          <Link
            to="/dashboard"
            className="inline-flex items-center justify-center rounded-lg bg-teal-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-teal-300"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    </section>
  );
}

function AppRoutes() {
  const { isAuthLoading } = useAuth();

  if (isAuthLoading) {
    return <AuthBootScreen />;
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/drivers" element={<Drivers />} />
          <Route path="/vehicles" element={<Vehicles />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/optimization" element={<Optimization />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
