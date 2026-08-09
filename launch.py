"""Hardware-independent launch wait loop."""


def accel_launch(qmi8658, sensitivity=0):
    """Wait for the existing all-axis threshold condition.

    The launch algorithm itself remains tracked by issue #3. Keeping the loop in
    this importable module allows deterministic regression tests around it.
    """
    ac_x = 0
    ac_y = 0
    ac_z = 0
    while ac_x < sensitivity or ac_y < sensitivity or ac_z < sensitivity:
        xyz = qmi8658.Read_XYZ()
        ac_x = xyz[0]
        ac_y = xyz[1]
        ac_z = xyz[2]
    return True
