import assert from "node:assert/strict";
import test from "node:test";
import { resolveHccrDashboardState } from "./researchHccrDashboardState.js";

test("research dashboard distinguishes loading, error, partial and available states", () => {
  assert.equal(resolveHccrDashboardState("loading", null).status, "loading");
  assert.equal(resolveHccrDashboardState("error", null, "API unavailable").message, "API unavailable");
  assert.equal(resolveHccrDashboardState("partial", { status: "partial", missing_artifacts: ["routing.csv"] }).message, "routing.csv");
  assert.equal(resolveHccrDashboardState("success", { status: "available" }).status, "success");
});
