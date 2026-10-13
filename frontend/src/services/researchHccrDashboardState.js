export function resolveHccrDashboardState(status, payload, message = "") {
  if (status === "loading") {
    return { status: "loading", message: "Loading frozen HCCR research outputs..." };
  }
  if (status === "error") {
    return { status: "error", message: message || "Research artifacts could not be loaded." };
  }
  if (!payload) {
    return { status: "empty", message: "No HCCR research payload is available." };
  }
  if (payload.status !== "available") {
    return {
      status: "partial",
      message: (payload.missing_artifacts || []).join(", "),
    };
  }
  return { status: "success", message: "" };
}
