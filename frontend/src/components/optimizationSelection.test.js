import assert from "node:assert/strict";
import test from "node:test";
import {
  getDriverLabel,
  getDriverSelectionIssue,
  getOrderSelectionIssue,
  getVehicleLabel,
  getVehicleStatus,
} from "./optimizationSelection.js";

test("selection labels use real driver and vehicle identifiers", () => {
  assert.equal(
    getDriverLabel({ full_name: "Asha Sen", license_number: "WB-L-42", id: "driver-id" }),
    "Asha Sen · WB-L-42",
  );
  assert.equal(
    getVehicleLabel({ registration_number: "WB-01-A", manufacturer: "Tata", model: "Ace" }),
    "WB-01-A · Tata · Ace",
  );
  assert.equal(getVehicleStatus({ status: "available", is_active: true }), "available · Active");
});

test("driver eligibility follows actual assigned vehicle and availability fields", () => {
  const vehicle = {
    id: "vehicle-1",
    status: "available",
    is_active: true,
  };
  const driver = {
    id: "driver-1",
    vehicle_id: vehicle.id,
    status: "available",
    is_available: true,
  };

  assert.equal(getDriverSelectionIssue(driver, [vehicle]), null);
  assert.match(
    getDriverSelectionIssue({ ...driver, status: "busy" }, [vehicle]),
    /not currently available/,
  );
  assert.match(
    getDriverSelectionIssue(driver, [{ ...vehicle, is_active: false }]),
    /unavailable or inactive/,
  );
  assert.match(getDriverSelectionIssue({ ...driver, vehicle_id: null }, [vehicle]), /No vehicle/);
});

test("delivered, cancelled, and invalid-location orders are not selectable", () => {
  const valid = { status: "pending", delivery_latitude: 22.57, delivery_longitude: 88.36 };

  assert.equal(getOrderSelectionIssue(valid), null);
  assert.match(getOrderSelectionIssue({ ...valid, status: "cancelled" }), /cancelled/);
  assert.match(getOrderSelectionIssue({ ...valid, status: "delivered" }), /delivered/);
  assert.match(getOrderSelectionIssue({ ...valid, delivery_longitude: 200 }), /coordinates/);
});