import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
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

test("forecast readiness keeps history context without Optimization limitation warnings", () => {
  const view = buildForecastReadinessView({ status: "success", capacityUnavailable: true }, 4);
  assert.equal(view.state, "success");
  assert.equal("calibrationMessage" in view, false);
  assert.equal("capacityMessage" in view, false);
  assert.match(view.historyMessage, /4 daily observations/);
});

test("Optimization readiness source does not render the removed advisory messages", () => {
  const formSource = readFileSync(new URL("./OptimizationForm.jsx", import.meta.url), "utf8");
  const readinessSource = readFileSync(new URL("./forecastReadinessView.js", import.meta.url), "utf8");
  const removedMessages = [
    ["Select an available", " vehicle to compare"],
    ["Synthetic demand units are", " not validated"],
    ["Paper-defined HCCR is", " not implemented"],
  ].map((parts) => parts.join(""));
  for (const message of removedMessages) {
    assert.equal(formSource.includes(message) || readinessSource.includes(message), false, message);
  }
});