"""Frame-accurate movement maths, following the engine order read from the decomp:
each game frame: velocity.y += gravity (not below -20); position += velocity * 1.5.
"""
import math

import player_moves as M

SCALE = M.POSITION_SCALE
FPS = M.FRAMES_PER_SECOND


def simulate_jump(speed_xz, velocity_y, gravity, slope_deg=0.0, max_frames=200):
    """Jump from flat ground (or straight up/down a slope of slope_deg). Returns airtime, peak height above the
    takeoff point, horizontal distance and the per-frame path [(x, y)]."""
    rise = math.tan(math.radians(slope_deg))
    x = y = 0.0
    v = velocity_y
    path = []
    peak = 0.0
    for f in range(1, max_frames + 1):
        v = max(v + gravity, -20.0)
        x += speed_xz * SCALE
        y += v * SCALE
        peak = max(peak, y)
        path.append((round(x, 2), round(y, 2)))
        if y <= x * rise and f > 1:
            return dict(airtime_frames=f, peak_height=round(peak, 2), distance=round(x, 2),
                        landing_height=round(x * rise, 2), path=path)
    return dict(airtime_frames=None, peak_height=round(peak, 2), distance=round(x, 2), path=path)


def jump_chain(speed_xz, velocity_y, gravity, slope_deg=0.0):
    """Repeated targeting jumps: airtime + 1 landing frame (the landing frame still moves at speed - 1, from
    func_80843E64's Math_StepToF(speed, 0, 1)), then the next jump starts. Derived from the code's action order."""
    j = simulate_jump(speed_xz, velocity_y, gravity, slope_deg)
    if j["airtime_frames"] is None:
        return None
    frames = j["airtime_frames"] + 1
    dist = j["distance"] + max(speed_xz - 1.0, 0.0) * SCALE
    return dict(frames_per_jump=frames, distance_per_jump=round(dist, 2), units_per_frame=round(dist / frames, 2))


def ground_target_speed(mode, multiplier, speed_cap, slope_deg=0.0):
    """Top speed a ground move reaches at full stick on a slope going uphill."""
    stick = M.SPEED_FORMULA["curved_full_stick"] if mode == "curved" else M.SPEED_FORMULA["linear_full_stick"]
    s = min(max(math.sin(math.radians(slope_deg)), 0.0), 0.6)
    target = min(max(stick * 0.14 - 8 * s * s, 0.0), speed_cap)
    return round(target * multiplier, 3)


def per_frame(speed):
    return round(speed * SCALE, 3)


def per_second(speed):
    return round(speed * SCALE * FPS, 2)
