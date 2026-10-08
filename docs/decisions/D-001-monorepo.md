# D-001: Monorepo

- Date: 2026-10-04
- Status: Accepted

## Decision

Keep hardware and software in a single repository (`LaMain`). `lamain-core`
stays an isolated, publishable library; the packages stay under `packages/` at
the repository root, following the uv workspace convention.

## Alternatives

- Separate repositories for hardware and software.
- One repository per component (core library, CLI, hardware).

## Rationale

Hardware revision and calibration are coupled: one tag identifies hand revision
+ firmware + calibration. A single history avoids keeping two repositories in
sync by hand.

## Accepted cost

A larger repository; contributors cloning the software also get the hardware
tree.

## Revisit if

A component must become confidential, or the repository becomes too large to
clone comfortably.
