# Benchmark tasks

Selection rule: a task enters the benchmark only if (1) the stock gripper fails
visibly, (2) success is binary, (3) a published comparable exists, or the
absence is stated.

Protocol: every task is run with tactile, without tactile, and with the stock
SO-101 gripper. The number of rollouts is fixed before running.

| # | Task | Proves | Published comparable |
|---|---|---|---|
| 1 | Pick-and-place, unknown mass | tactile | TacO arXiv:2605.21976; AnySkin arXiv:2409.08276 |
| 2 | Pick a flat object from a table | three fingers | none known |
| 3 | Plug insertion | tactile + industrial | eFlesh arXiv:2506.09994; T3 arXiv:2406.13640; TacO |
| 4 | In-hand reorientation | three fingers | TacO |
| 5 | Peg-in-hole, ~1 mm clearance | industrial | NIST Assembly Task Boards; arXiv:2406.05331 |
