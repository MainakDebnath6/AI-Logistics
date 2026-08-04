import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const redirectTo = location.state?.from?.pathname || "/dashboard";

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!email.trim() || !password.trim()) {
      setError("Email and password are required.");
      return;
    }

    setSubmitting(true);
    try {
      await login({ email: email.trim(), password });
      navigate(redirectTo, { replace: true });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Unable to sign in. Please check your credentials.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-100">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_12%_15%,rgba(20,184,166,0.26),transparent_40%),radial-gradient(circle_at_88%_20%,rgba(14,165,233,0.18),transparent_42%)]" />
      <div className="relative mx-auto flex min-h-screen w-full max-w-6xl items-center px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid w-full gap-10 lg:grid-cols-2 lg:gap-16">
          <section className="hidden lg:block">
            <p className="inline-flex rounded-full border border-teal-300/30 bg-teal-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-teal-200">
              AI Logistics Control Center
            </p>
            <h1 className="mt-5 text-5xl font-black leading-tight text-white">
              Dispatch Faster.
              <span className="block text-teal-300">Deliver Smarter.</span>
            </h1>
            <p className="mt-4 max-w-xl text-base text-slate-300">
              Secure dispatcher and admin access to operations, optimization,
              drivers, vehicles, orders, and performance analytics.
            </p>
          </section>

          <section className="mx-auto w-full max-w-md self-center">
            <div className="rounded-2xl border border-white/10 bg-slate-900/75 p-6 shadow-2xl backdrop-blur sm:p-8">
              <h2 className="text-2xl font-bold text-white">Sign In</h2>
              <p className="mt-1 text-sm text-slate-300">
                Use your dispatcher or admin account.
              </p>

              <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
                <div>
                  <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-slate-200">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    disabled={submitting}
                    required
                    className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2.5 text-sm text-white outline-none ring-teal-400 placeholder:text-slate-500 focus:border-teal-400 focus:ring-2"
                    placeholder="dispatcher@company.com"
                  />
                </div>

                <div>
                  <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-slate-200">
                    Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    disabled={submitting}
                    required
                    className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2.5 text-sm text-white outline-none ring-teal-400 placeholder:text-slate-500 focus:border-teal-400 focus:ring-2"
                    placeholder="••••••••"
                  />
                </div>

                {error ? (
                  <p className="rounded-lg border border-rose-400/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
                    {error}
                  </p>
                ) : null}

                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex w-full items-center justify-center rounded-lg bg-teal-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-teal-300 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {submitting ? "Signing in..." : "Sign In"}
                </button>
              </form>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
