# LeRobot integration

## Plan

Ship a separate package `lerobot_robot_lamain`, depending on `lamain-core`.

The `lerobot_robot_` prefix is required for LeRobot plugin auto-discovery, so
the hand is used with `--robot.type=lamain`.

## Joint mapping (lamain-core <-> LeRobot)

TODO(arthur): map each LeRobot motor/feature name to the `lamain-core` joint
names (`index_flex`, `middle_flex`, `index_middle_abd`, `thumb_rot`,
`thumb_flex`).
