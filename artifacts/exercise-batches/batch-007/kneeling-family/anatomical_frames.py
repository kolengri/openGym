"""Two-axis knee frames from the immutable source and actual FK hinge plane."""

def knee_frames(a, side, hip, knee, ankle, fallback_rotation):
    """Preserve the signed knee hinge, not just each bone's aimed direction.

    The authored cycles remain well away from straight knees. The deterministic
    fallback is only for a nearly straight target, where its cross product
    cannot define roll. Actual fallback use and angular margins are reported.
    """
    source_up = a.heads[side + 'Leg'] - a.heads[side + 'UpLeg']
    source_leg = a.heads[side + 'Foot'] - a.heads[side + 'Leg']
    source_normal = source_up.cross(source_leg).normalized()
    target_up = knee - hip
    target_leg = ankle - knee
    target_normal = target_up.cross(target_leg)
    sine = target_normal.length / (target_up.length * target_leg.length)
    fallback = sine < 1e-6
    if fallback:
        target_normal = fallback_rotation @ source_normal
        axis = target_up.normalized()
        target_normal -= axis * target_normal.dot(axis)
    target_normal.normalize()
    up_delta = (a.frame(target_up, target_normal) @
                a.frame(source_up, source_normal).transposed()).to_quaternion()
    leg_delta = (a.frame(target_leg, target_normal) @
                 a.frame(source_leg, source_normal).transposed()).to_quaternion()
    return (up_delta @ a.rest[side + 'UpLeg'].to_quaternion(),
            leg_delta @ a.rest[side + 'Leg'].to_quaternion(),
            {'fallback_used': fallback, 'hinge_sine': sine,
             'source_hinge_normal': list(source_normal),
             'target_hinge_normal': list(target_normal)})
