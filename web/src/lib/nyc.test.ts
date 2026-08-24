import assert from "node:assert/strict";
import { test } from "node:test";
import { bblError, binError, boroughFromBbl, digitsOnly } from "./nyc.ts";
import { reviewClock } from "./reviewClock.ts";

test("BBL requires 10 digits and a NYC borough", () => {
  assert.equal(digitsOnly("4-051-980021"), "4051980021");
  assert.equal(boroughFromBbl("4051980021"), "Queens");
  assert.equal(bblError(""), "Enter the 10-digit BBL.");
  assert.equal(bblError("123"), "BBL must be 10 digits (borough + block + lot).");
  assert.equal(bblError("0051980021"), "First BBL digit must be 1–5 (NYC borough).");
  assert.equal(bblError("4051980021"), null);
});

test("BIN is optional but must be 7 digits when present", () => {
  assert.equal(binError(""), null);
  assert.equal(binError("4117367"), null);
  assert.ok(binError("12"));
});

test("review clock is overdue after five calendar days", () => {
  const created = "2026-08-18T00:00:00.000Z";
  const now = new Date("2026-08-24T12:00:00.000Z");
  const clock = reviewClock(created, now);
  assert.equal(clock.kind, "overdue");
});
