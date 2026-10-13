import assert from "node:assert/strict";
import test from "node:test";
import { buildForecastReadinessView } from "./forecastReadinessView.js";

test("forecast readiness presents loading state", () => {
  assert.equal(buildForecastReadinessView({ status: "loading" }, 0, "loading").state, "loading");
});

test("forecast readiness reports empty history", () => {
  const view = buildForecastReadinessView({ status: "loading" }, 0, "empty");
  assert.equal(view.state, "empty");
  assert.match(view.message, /No demand history/);
});

test("forecast readiness reports source and prediction errors", () => {
  const sourceError = buildForecastReadinessView({ status: "loading" }, 0, "error");
  const predictionError = buildForecastReadinessView({ status: "error", message: "API unavailable" }, 20);
  assert.match(sourceError.message, /route optimization remains available/);
  assert.match(predictionError.message, /API unavailable/);
});

test("forecast readiness success identifies missing calibration and capacity scope", () => {
  const view = buildForecastReadinessView({ status: "success", capacityUnavailable: true }, 4);
  assert.equal(view.state, "success");
  assert.match(view.calibrationMessage, /Paper-defined HCCR is not implemented/);
  assert.match(view.capacityMessage, /no fleet availability schedule/);
  assert.match(view.historyMessage, /4 daily observations/);
});