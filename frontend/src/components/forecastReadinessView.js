export function buildForecastReadinessView(readiness, historyCount, sourceStatus) {
  if (sourceStatus === "loading") {
    return {
      state: "loading",
      message: "Loading synthetic demand history and forecast...",
    };
  }
  if (sourceStatus === "empty") {
    return {
      state: "empty",
      message: "No demand history is available; forecast and capacity risk are unavailable.",
    };
  }
  if (sourceStatus === "error") {
    return {
      state: "error",
      message: "Synthetic demand history could not be loaded; route optimization remains available.",
    };
  }
  if (!readiness || readiness.status === "loading") {
    return {
      state: "loading",
      message: "Loading synthetic demand history and forecast...",
    };
  }
  if (readiness.status === "empty") {
    return {
      state: "empty",
      message: "No demand history is available; forecast and capacity risk are unavailable.",
    };
  }
  if (readiness.status === "error") {
    return {
      state: "error",
      message: readiness.message
        ? `Forecast unavailable: ${readiness.message}`
        : "Synthetic demand history could not be loaded; route optimization remains available.",
    };
  }

  return {
    state: "success",
    historyMessage: historyCount < 7
      ? `Limited history: only ${historyCount} daily observations are available.`
      : null,
  };
}