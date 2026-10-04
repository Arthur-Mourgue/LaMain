# D-002: Rigid four-bar linkages instead of tendons

- Date: 2026-10-04
- Status: Accepted

## Decision

Use rigid four-bar linkages rather than tendon-driven fingers.

## Alternatives

- Tendon-driven fingers (cable + return spring).

## Rationale

Tendon tension depends on who assembled the hand and drifts over time (creep,
friction hysteresis, re-tensioning): per-unit variability is incompatible with
transferring data across hand instances. A rigid linkage is repeatable from one
instance to the next.

## Accepted cost

Packaging inside the 12 x 15 mm phalanx section, and solving a four-pivot
synthesis.

## Revisit if

The synthesis cannot reach a coupling k close to 1 over 0-95 deg.
