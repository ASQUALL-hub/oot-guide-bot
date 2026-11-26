"""Curated knowledge about Link's actions and movement, for bots.

Every number marked with a `src` entry was read from the zeldaret/oot decomp. make_metadata.py checks that each
`src` snippet still appears verbatim in that file, so a decomp update can't silently invalidate these values.
Values are per GAME FRAME. NTSC OoT runs 20 game frames per second, and positions move by velocity x 1.5 per
frame (R_UPDATE_RATE = 3, Actor_UpdatePos uses R_UPDATE_RATE * 0.5).

`verified`: "code" means the effect was read from the decomp; "community" means it's speedrunning knowledge
that this database has NOT checked against the code (treat it as a hint).
"""

P = "src/overlays/actors/ovl_player_actor/z_player.c"
PL = "src/code/z_player_lib.c"

FRAMES_PER_SECOND = 20
POSITION_SCALE = 1.5  # world units moved per frame = velocity * 1.5

ENGINE = {
    "frames_per_second": dict(value=20, src=("src/code/game.c", "R_UPDATE_RATE = 3;"),
                              note="game logic runs every 3 video frames (60 Hz / 3)"),
    "position_scale": dict(value=1.5, src=("src/code/z_actor.c", "f32 speedRate = R_UPDATE_RATE * 0.5f;"),
                           note="position += velocity * 1.5 each game frame"),
    "per_frame_order": "velocity.y += gravity (min -20), then position += velocity * 1.5, then collision",
    "max_fall_velocity": dict(value=-20.0, src=(P, "this->actor.minVelocityY = FRAMERATE_CONST(-20.0f, -24.0f);")),
    "stick_magnitude_max": dict(value=60, src=("src/code/z_lib.c", "*outMagnitude = (60.0f < *outMagnitude) ? 60.0f : *outMagnitude;")),
}

# Speed limits and gravity by boots (z_player_lib.c sBootData, applied by Player_SetBootData).
BOOTS = [
    dict(boots="Kokiri (adult)", run_speed_limit=6.0, gravity=-1.0, accel=2.0, src=(PL, "600,                         // R_RUN_SPEED_LIMIT")),
    dict(boots="Kokiri (child)", run_speed_limit=5.5, gravity=-1.0, accel=2.0, src=(PL, "550,                         // R_RUN_SPEED_LIMIT")),
    dict(boots="Hover", run_speed_limit=5.5, gravity=-1.0, accel=2.0, src=(PL, "// PLAYER_BOOTS_HOVER")),
    dict(boots="Iron", run_speed_limit=3.0, gravity=-1.6, accel=2.0, src=(PL, "300,                         // R_RUN_SPEED_LIMIT")),
    dict(boots="Iron (underwater)", run_speed_limit=5.5, gravity=-0.4, accel=0.8, src=(PL, "-40,                       // REG(68)")),
    dict(boots="any, in a room marked indoors", run_speed_limit=5.0, gravity=None, accel=None, src=(PL, "R_RUN_SPEED_LIMIT = 500;")),
]

SPEED_FORMULA = dict(
    text=("target = stick_term * 0.14 - 8 * s^2, clamped to [0, speed cap], where s = clamp(sin(floor pitch), 0, 0.6). "
          "stick_term at full stick (60): normal running ('curved') = 46.97, Z-targeted movement ('linear') = 48.0 "
          "(60 * 0.8). Speed moves toward the target by +2.0/-1.5 per frame (Kokiri boots)."),
    src=(P, "*outSpeedTarget = (*outSpeedTarget * 0.14f) - (8.0f * floorPitchInfluence * floorPitchInfluence);"),
    curved_full_stick=46.97, linear_full_stick=48.0,
)

# Jumps: simulated by build_actions.py (frames in the air, peak height, distance).
JUMPS = [
    dict(id="sidehop", name="Sidehop", inputs="hold Z (target or not) + stick left/right + A",
         speed_xz=8.5, velocity_y=3.5, direction="90 degrees left/right of facing", momentum="locked",
         conditions="not in a room marked indoors; not on floor type 7 or a floor with floor_effect 1",
         landing_anims=["gPlayerAnim_link_fighter_Lside_jump_end", "gPlayerAnim_link_fighter_Rside_jump_end"],
         air_anims=["gPlayerAnim_link_fighter_Lside_jump"],
         src=[(P, "func_80838940(this, D_80853D4C[controlStickDirection][0], !(controlStickDirection & 1) ? 5.8f : 3.5f, play,"),
              (P, "this->speedXZ = !(controlStickDirection & 1) ? 6.0f : 8.5f;"),
              (P, "(play->roomCtx.curRoom.type != ROOM_TYPE_INDOORS)")]),
    dict(id="backflip", name="Backflip", inputs="hold Z + stick back + A",
         speed_xz=6.0, velocity_y=5.8, direction="straight backward (Link keeps facing forward)", momentum="locked",
         conditions="same as sidehop",
         landing_anims=["gPlayerAnim_link_fighter_backturn_jump_end"], air_anims=["gPlayerAnim_link_fighter_backturn_jump"],
         src=[(P, "func_80838940(this, D_80853D4C[controlStickDirection][0], !(controlStickDirection & 1) ? 5.8f : 3.5f, play,"),
              (P, "this->speedXZ = !(controlStickDirection & 1) ? 6.0f : 8.5f;")]),
    dict(id="jumpslash", name="Jumpslash", inputs="hold Z + stick neutral/forward + A, with a sword out (no sword: rolls instead)",
         speed_xz=5.0, velocity_y=5.0, direction="forward", momentum="set by the attack",
         conditions="same as sidehop", landing_anims=[], air_anims=[],
         src=[(P, "func_8083BA90(play, this, PLAYER_MWA_JUMPSLASH_START, 5.0f, 5.0f);")]),
    dict(id="air_jumpslash", name="Jumpslash out of a jump", inputs="press B while airborne from a jump, with a sword",
         speed_xz=3.0, velocity_y=4.5, direction="forward", momentum="set by the attack",
         conditions="sword held, not shielding", landing_anims=[], air_anims=[],
         src=[(P, "func_8083BA90(play, this, PLAYER_MWA_JUMPSLASH_START, 3.0f, 4.5f);")]),
    dict(id="auto_jump_full_speed", name="Run off a ledge (auto-jump), full speed", inputs="run off an edge faster than 5.9 (adult) / 5.4 (child)",
         speed_xz=6.0, velocity_y=7.5, direction="forward", momentum="steerable (stick keeps control; >135 degree turn brakes 1.0/frame)",
         conditions="drop below the edge > 20 units, speed > 3, moving within ~45 degrees of facing, no sword swing",
         landing_anims=["gPlayerAnim_link_normal_run_jump_end"], air_anims=["gPlayerAnim_link_normal_run_jump"],
         src=[(P, "temp = IREG(67) / 100.0f;"), (PL, "750,                         // IREG(67)")]),
    dict(id="auto_jump_slow", name="Run off a ledge (auto-jump), slower", inputs="walk off an edge at speed 3-5.9",
         speed_xz=4.0, velocity_y=2.05, direction="forward", momentum="steerable",
         conditions="upward speed = 1.25 + 0.2 x speed (adult), 1.25 + 0.4 x speed (child). Example at speed 4.0 (adult)",
         landing_anims=[], air_anims=["gPlayerAnim_link_normal_jump"],
         src=[(P, "temp = (IREG(68) / 100.0f) + ((IREG(69) * this->speedXZ) / 1000.0f);")]),
    dict(id="ledge_hop", name="Hop up a small ledge", inputs="walk into a ledge lower than 41 (adult) / 27 (child) for 3 frames",
         speed_xz=2.5, velocity_y=None, direction="forward", momentum="fixed",
         conditions="upward speed = 5.5 + 0.08 x ledge height",
         landing_anims=[], air_anims=["gPlayerAnim_link_normal_jump"],
         src=[(P, "temp = (this->yDistToLedge * 0.08f) + 5.5f;"), (P, "this->speedXZ = 2.5f;")]),
]

GRAVITY_CASES = [
    dict(case="normal", gravity=-1.0, src=(PL, "-100,                        // REG(68)")),
    dict(case="while locked on to a hostile enemy", gravity=-1.2, src=(P, "this->actor.gravity = -1.2f;")),
]

GROUND_MOVES = [
    dict(id="run", name="Run", inputs="stick, no Z", mode="curved", multiplier=1.0, cap="run speed limit",
         note="the normal way to move; turning more than ~135 degrees above speed 6 forces a brake skid",
         src=[(P, "Player_GetMovementSpeedAndYaw(this, &speedTarget, &yawTarget, SPEED_MODE_CURVED, play);")]),
    dict(id="z_walk_forward", name="Z-targeted forward movement", inputs="hold Z + stick forward",
         mode="linear", multiplier=1.0, cap="run speed limit", note="facing stays locked",
         src=[(P, "Player_GetMovementSpeedAndYaw(this, &speedTarget, &yawTarget, SPEED_MODE_LINEAR, play);")]),
    dict(id="backwalk", name="Backwalk (Z + back)", inputs="hold Z + stick backward (relative to facing)",
         mode="linear", multiplier=1.5, cap="run speed limit (before the x1.5)",
         note=("1.5x the normal target speed: 9.0 vs running's 6.0 on flat ground (adult). Link moves backward, so "
               "turn 180 degrees first to backwalk toward a goal"),
         src=[(P, "Math_AsymStepToF(&this->speedXZ, speedTarget * 1.5f, 1.5f, 2.0f);")]),
    dict(id="roll", name="Roll", inputs="A while moving forward (not targeting)", mode="curved", multiplier=1.5, cap=None,
         note=("target = 1.5 x walking target, minimum 3.0. A roll at speed 7.0+ into a wall/actor bonks (bounces back). "
               "Animation 'landing_roll' plays at 1.25x"),
         src=[(P, "speedTarget *= 1.5f;"), (P, "// Must have a speed of 7 or above to be able to bonk into something")]),
]

RULES = [
    dict(rule="Brake skid when turning around while running",
         effect="turning the stick more than ~135 degrees (0x6000) while faster than 6.0 plays 'back_brake' (Link skids to a stop, then turns)",
         src=[(P, "if (this->speedXZ > 6.0f) {"), (P, "Player_AnimChangeOnceMorph(play, this, &gPlayerAnim_link_normal_back_brake);")]),
    dict(rule="Z with nothing to target locks facing ('parallel' mode)",
         effect="pressing Z stores Link's current facing; movement then strafes/backwalks without turning. If Link is pushing a wall he snaps to face it",
         src=[(P, "this->parallelYaw = this->actor.shape.rot.y;")]),
    dict(rule="Targeting jumps are blocked indoors",
         effect="sidehop/backflip/jumpslash via Z+A only work when the current room isn't type 'indoors' and the floor isn't type 7 / floor_effect 1",
         src=[(P, "(play->roomCtx.curRoom.type != ROOM_TYPE_INDOORS)")]),
    dict(rule="Indoor speed cap", effect="run speed limit drops to 5.0 in rooms marked indoors",
         src=[(PL, "R_RUN_SPEED_LIMIT = 500;")]),
    dict(rule="Slopes slow walking, not targeting jumps",
         effect="walking/backwalking lose 8 x s^2 from their target speed (s = sin(slope), max 0.6); sidehop/backflip momentum is locked in the air",
         src=[(P, "*outSpeedTarget = (*outSpeedTarget * 0.14f) - (8.0f * floorPitchInfluence * floorPitchInfluence);")]),
    dict(rule="Fall damage", effect="falls of 400-799 units: -8 health (half a heart); 800+: -16 (one heart). Floor types 6 and 9 never hurt",
         src=[(P, "if (fallDistance >= 400) {"), (P, "{ -8, 180, 40, 100, NA_SE_VO_LI_LAND_DAMAGE_S },"),
              (P, "{ -16, 255, 140, 150, NA_SE_VO_LI_LAND_DAMAGE_S },")]),
    dict(rule="Roll on landing skips fall damage",
         effect="landing from a fall of 81-799 units with the stick held forward (not carrying anything) starts a roll and skips the fall-damage check",
         src=[(P, "} else if ((this->fallDistance < 800) &&"), (P, "Player_SetupRoll(this, play);")]),
    dict(rule="Hover Boots", effect="after leaving the ground Link stays airborne ~19 frames (vertical speed held at 1.0); run limit 5.5",
         src=[(P, "this->hoverBootsTimer = 19;"), (P, "this->actor.velocity.y = 1.0f;")]),
    dict(rule="Targeting jumps chain with ~1 frame of landing lag",
         effect=("landing with Z held enters a targeting idle state that checks for the next Z+A jump every frame, even "
                 "while the landing animation plays, so the next hop can start the frame after landing"),
         src=[(P, "if (!Player_TryActionHandlerList(play, this, sActionHandlerList1, true)) {"),
              (P, "PLAYER_ACTION_HANDLER_10, PLAYER_ACTION_HANDLER_11, PLAYER_ACTION_HANDLER_8,    -PLAYER_ACTION_HANDLER_7,"),
              (P, "actionFunc = Player_Action_808407CC;")]),
    dict(rule="Momentum during targeting jumps",
         effect="while a sidehop/backflip is in the air (PLAYER_STATE2_19) the stick does not change speed or direction",
         src=[(P, "if (!(this->stateFlags2 & PLAYER_STATE2_19)) {")]),
]

TECH = [
    dict(name="Sidehop chaining", inputs="Z + left/right + A, repeated",
         what=("each hop moves 8.5 x 1.5 = 12.75 units/frame sideways while airborne, and the next hop can start one frame "
               "after landing (Z held). Chained, that's ~12.5 units/frame vs 9.0 running (adult, flat): ~39% faster. "
               "Momentum is locked, so slopes don't slow the airborne part: from ~25-30 degrees uphill it beats backwalking"),
         best_for="steep uphill outdoors (on flat ground backwalking is faster: 13.5 vs 12.5 units/frame)",
         verified="code (velocities, action order); the 1-frame landing gap is derived from the code, not measured in an emulator"),
    dict(name="Turn around, then backwalk", inputs="face away from the goal, hold Z, hold stick back",
         what=("backwalk targets 1.5x the normal speed (9.0 vs 6.0 adult, flat ground; 8.25 vs 5.5 child). "
               "Uphill it keeps the 1.5x, so it beats running on slopes too"),
         best_for=("the fastest ground movement on flat and gentle slopes (13.5 units/frame adult); also indoors, "
                   "where sidehops are disabled. Past ~25-30 degrees uphill, switch to sidehops"), verified="code"),
    dict(name="Target turnaround (180 degree turn)", inputs="hold Z to lock facing, then move/backwalk; or stop and turn in place",
         what=("turning >135 degrees while running above 6.0 forces the 12-frame brake skid. Z locks facing, so you can "
               "reverse direction by backwalking/backflipping instead of turning"),
         best_for="reversing direction without the skid", verified="code (skid rule); exact fastest input is community knowledge"),
    dict(name="Backflip to reverse", inputs="Z + back + A", what="moves 6.0 x 1.5 = 9 units/frame backward, peak ~15 units, no turn",
         best_for="quick reversal, hopping back over small gaps", verified="code"),
    dict(name="Roll", inputs="A while running", what="up to 9.0 speed (1.5x walking target); bonks at 7.0+ into walls",
         best_for="short bursts; roll on landing to skip fall damage", verified="code"),
    dict(name="Roll landing to skip fall damage", inputs="hold stick forward while landing from 81-799 units",
         what="starts a roll instead of taking fall damage", best_for="dropping off cliffs", verified="code"),
    dict(name="Jumpslash", inputs="Z + A with sword (or B in midair)", what="5.0 speed / 5.0 upward (3.0 / 4.5 from midair)",
         best_for="crossing small gaps, hitting switches", verified="code"),
]

# Glitch / advanced names the OoT Randomizer uses (logic/helpers.json). Descriptions are community knowledge.
COMMUNITY_GLITCHES = [
    dict(name="Infinite Sword Glitch (ISG)", logic_name="glitch_isg", what="keeps the sword's hitbox active indefinitely after an interrupted crouch stab"),
    dict(name="Megaflip", logic_name="glitch_megaflip", what="backflip/sidehop boosted by explosion recoil while shielding, for a very long jump"),
    dict(name="Hover (bomb hover)", logic_name="glitch_hovering", what="gaining height in midair with repeated explosion recoil"),
    dict(name="Superslide", logic_name="glitch_superslide", what="keeps high speed from recoil while sliding/shielding"),
    dict(name="Hookshot jump", logic_name="glitch_hookshot_jump", what="using the hookshot to gain height off certain surfaces"),
    dict(name="Weirdshot", logic_name="glitch_weirdshot", what="hookshot/bow interaction that warps Link through geometry"),
    dict(name="Ground jump", logic_name="glitch_groundjump", what="jumping from the ground using a held bomb/explosion"),
    dict(name="Ocarina items (OI)", logic_name="glitch_oi", what="using an item from the ocarina/bottle menu state to get it early"),
    dict(name="Equip swap", logic_name="glitch_equip_swap", what="using items with the other age's restrictions bypassed"),
    dict(name="Recoil jump", logic_name="adv_recoil_jump", what="gaining distance from attack/shield recoil"),
    dict(name="Damage boost", logic_name="adv_damage_boost", what="taking a hit to be knocked across a gap or onto a ledge"),
    dict(name="Hover boots recoil", logic_name="adv_hovers_recoil", what="combining hover boots with recoil to cross large gaps"),
]

# Labels for every Player_Action_* function, identified from the animations, sounds and state flags each one
# uses (evidence is in data/meta/player_actions.json). confidence: high / medium / low.
ACTION_LABELS = {
    "Player_Action_80840450": ("Idle while locked on to an enemy (also where targeting jumps land)", "targeting", "high"),
    "Player_Action_808407CC": ("Idle with Z held: no target or a friendly target (also where targeting jumps land)", "targeting", "high"),
    "Player_Action_Idle": ("Standing idle", "idle", "high"),
    "Player_Action_80840DE4": ("Z-targeted slow walk (forward)", "targeting", "medium"),
    "Player_Action_808414F8": ("Z-targeted backwalk (1.5x speed)", "targeting", "high"),
    "Player_Action_8084170C": ("Brake skid after turning around at speed", "movement", "high"),
    "Player_Action_808417FC": ("End of the brake skid", "movement", "high"),
    "Player_Action_8084193C": ("Z-targeted strafe (side walk)", "targeting", "high"),
    "Player_Action_TurnInPlace": ("Turning in place", "movement", "high"),
    "Player_Action_80842180": ("Running (normal)", "movement", "high"),
    "Player_Action_8084227C": ("Running while Z-targeting", "targeting", "medium"),
    "Player_Action_808423EC": ("Z-targeted back-step (start of backing up)", "targeting", "high"),
    "Player_Action_8084251C": ("Z-targeted back-step stop", "targeting", "high"),
    "Player_Action_8084279C": ("Holding up / checking an item", "items", "medium"),
    "Player_Action_80843188": ("Shield raised (R held)", "combat", "high"),
    "Player_Action_808435C4": ("Raising the shield", "combat", "high"),
    "Player_Action_8084370C": ("Hit / staggered by damage", "damage", "high"),
    "Player_Action_8084377C": ("Knocked down (also frozen / electrocuted)", "damage", "high"),
    "Player_Action_80843954": ("Getting up after a knockdown", "damage", "high"),
    "Player_Action_80843A38": ("Recovering after getting up", "damage", "medium"),
    "Player_Action_80843CEC": ("Dying / revived by a fairy", "damage", "high"),
    "Player_Action_8084411C": ("In the air (jump, sidehop, backflip, falling)", "movement", "high"),
    "Player_Action_Roll": ("Rolling", "movement", "high"),
    "Player_Action_80844A44": ("Jumping/falling into deep water", "water", "high"),
    "Player_Action_80844AF4": ("Jumpslash (airborne attack)", "combat", "high"),
    "Player_Action_80844E68": ("Charging a spin attack (B held)", "combat", "high"),
    "Player_Action_80845000": ("Walking while charging a spin attack", "combat", "medium"),
    "Player_Action_80845308": ("Strafing while charging a spin attack", "combat", "medium"),
    "Player_Action_80845668": ("Climbing up onto a ledge", "movement", "high"),
    "Player_Action_WaitForPutAway": ("Putting away the held item first", "items", "high"),
    "Player_Action_80845CA4": ("Walking into a loading zone / scene exit", "transitions", "high"),
    "Player_Action_80845EF8": ("Walking through a door", "transitions", "high"),
    "Player_Action_80846050": ("Lifting an object", "carry", "high"),
    "Player_Action_80846120": ("Lifting a heavy object (Gauntlets)", "carry", "medium"),
    "Player_Action_80846260": ("Holding a huge rock overhead (Silver/Golden Gauntlets)", "carry", "high"),
    "Player_Action_80846358": ("Throwing a huge rock", "carry", "high"),
    "Player_Action_80846408": ("Failing to lift (too heavy)", "carry", "high"),
    "Player_Action_808464B0": ("Putting down a carried object", "carry", "high"),
    "Player_Action_80846578": ("Throwing a carried object", "carry", "high"),
    "Player_Action_8084B1D8": ("Using an item (first-person / aiming state)", "items", "low"),
    "Player_Action_Talk": ("Talking", "interaction", "high"),
    "Player_Action_8084B78C": ("Grabbing a block", "interaction", "medium"),
    "Player_Action_8084B898": ("Pushing a block", "interaction", "high"),
    "Player_Action_8084B9E4": ("Pulling a block", "interaction", "high"),
    "Player_Action_8084BBE4": ("Hanging from a ledge", "climbing", "high"),
    "Player_Action_8084BDFC": ("Pulling up from a ledge hang", "climbing", "high"),
    "Player_Action_8084BF1C": ("Climbing a ladder / vines", "climbing", "high"),
    "Player_Action_8084C5F8": ("Grabbing a ladder from the top", "climbing", "medium"),
    "Player_Action_8084C760": ("Getting on/off a climbing surface", "climbing", "low"),
    "Player_Action_8084C81C": ("Crawling through a crawlspace (child)", "movement", "high"),
    "Player_Action_8084CC98": ("Riding Epona", "horse", "high"),
    "Player_Action_8084D3E4": ("Getting off Epona", "horse", "high"),
    "Player_Action_8084D610": ("Treading water at the surface", "water", "high"),
    "Player_Action_8084D7C4": ("Starting to swim", "water", "medium"),
    "Player_Action_8084D84C": ("Swimming at the surface", "water", "medium"),
    "Player_Action_8084DAB4": ("Swimming (turning / alternate stroke)", "water", "low"),
    "Player_Action_8084DC48": ("Diving / swimming underwater", "water", "high"),
    "Player_Action_8084E1EC": ("Surfacing for breath", "water", "high"),
    "Player_Action_8084E30C": ("Hit while in water", "water", "medium"),
    "Player_Action_8084E368": ("Drowning / dying in water", "water", "medium"),
    "Player_Action_8084E3C4": ("Playing the ocarina", "items", "high"),
    "Player_Action_8084E604": ("Finishing an item action (e.g. after a hookshot/bomb move)", "items", "low"),
    "Player_Action_8084E6D4": ("Opening a chest / receiving an item", "items", "high"),
    "Player_Action_TimeTravelEnd": ("Arriving after time travel", "cutscene", "high"),
    "Player_Action_8084EAC0": ("Drinking from a bottle", "items", "high"),
    "Player_Action_SwingBottle": ("Swinging a bottle to catch something", "items", "high"),
    "Player_Action_8084EED8": ("Releasing a bottled bug/fish/fairy", "items", "medium"),
    "Player_Action_8084EFC0": ("Dropping a fish / releasing bottle contents", "items", "medium"),
    "Player_Action_ExchangeItem": ("Showing or giving an item to someone", "items", "high"),
    "Player_Action_8084F308": ("Grabbed by a ReDead", "damage", "high"),
    "Player_Action_SlideOnSlope": ("Sliding down a steep slope", "movement", "high"),
    "Player_Action_WaitForCutscene": ("Waiting for a cutscene", "cutscene", "high"),
    "Player_Action_StartWarpSongArrive": ("Arriving by warp song", "transitions", "high"),
    "Player_Action_BlueWarpArrive": ("Arriving by blue warp", "transitions", "high"),
    "Player_Action_8084F88C": ("Falling into a pit / void-out exit", "transitions", "medium"),
    "Player_Action_TryOpeningDoor": ("Opening a door", "transitions", "high"),
    "Player_Action_ExitGrotto": ("Jumping out of a grotto", "transitions", "high"),
    "Player_Action_8084FA54": ("Interaction state entered from talking (e.g. Navi / special talk)", "interaction", "low"),
    "Player_Action_8084FB10": ("Frozen in ice", "damage", "high"),
    "Player_Action_8084FBF4": ("Grabbed and carried away (Wallmaster / Like Like style)", "damage", "medium"),
    "Player_Action_808502D0": ("Landing from a jumpslash", "combat", "high"),
    "Player_Action_808505DC": ("Recoil after an attack is blocked", "combat", "medium"),
    "Player_Action_8085063C": ("Casting Farore's Wind", "magic", "high"),
    "Player_Action_FaroresWindArrive": ("Arriving by Farore's Wind", "magic", "high"),
    "Player_Action_808507F4": ("Casting Din's Fire / Nayru's Love", "magic", "high"),
    "Player_Action_HookshotFly": ("Flying with the hookshot", "items", "high"),
    "Player_Action_80850C68": ("Fishing (reeling)", "minigame", "high"),
    "Player_Action_80850E84": ("Catching a fish", "minigame", "high"),
    "Player_Action_CsAction": ("Controlled by a cutscene", "cutscene", "high"),
}


# ---------------------------------------------------------------------------------------------------------------
# Link's body, hitboxes, world collision and frame order. Model-space values convert to world units by Link's
# actor scale (0.01, set for every actor in Actor_Init and never changed for the player).
ACT = "src/code/z_actor.c"
BG = "src/code/z_bgcheck.c"
PLAY = "src/code/z_play.c"
PROF = "include/actor_profile.h"
PLIB = "src/code/z_player_lib.c"

BODY = [
    dict(part="Hurtbox (what enemies hit)", shape="cylinder", radius=12.0,
         height=("recomputed every frame: from the midpoint of Link's feet to his head + 10 (initial value 60); "
                 "x0.8 while shielding"),
         src=[(P, "{ 12, 60, 0, { 0, 0, 0 } },"), (P, "temp_f0 += this->bodyPartsPos[PLAYER_BODYPART_HEAD].y + 10.0f;"),
              (P, "this->cylinder.dim.height *= 0.8f;")]),
    dict(part="Wall check (what stops Link at walls)", shape="line test + sphere pushed out of walls",
         radius="18 adult, 14 child, 10 while crawling", height="checked at feet + 26 (feet + 15 while crawling)",
         src=[(P, "vWallCheckHeight = 26.0f;"), (P, "18.0f,            // wallCheckRadius"),
              (P, "14.0f,                   // wallCheckRadius"), (P, "vWallCheckRadius = 10.0f;")]),
    dict(part="Ceiling clearance", shape="upward check from last frame's height + 10",
         height="56 adult, 40 child, 30 while crawling (lower ceilings stop Link or need crawling)",
         src=[(P, "56.0f,            // ceilingCheckHeight"), (P, "40.0f,                   // ceilingCheckHeight"),
              (P, "ceilingCheckHeight = 30.0f;")]),
    dict(part="Floor detection", shape="ray cast straight down",
         height="starts 50 above last frame's height at the new X/Z; the first floor below is snapped to",
         src=[(ACT, "pos->y += 50.0f;")]),
    dict(part="Ledge detection", shape="ray cast down in front of Link",
         height="starts 111 (adult) / 71 (child) above his feet; ledges 18+ above him count",
         src=[(P, "ledgeCheckPos.y = this->actor.world.pos.y + this->ageProperties->unk_0C;"),
              (P, "if ((this->yDistToLedge < 18.0f) ||")]),
    dict(part="Model scale", shape="-", height="Link's model units x 0.01 = world units",
         src=[(ACT, "Actor_SetScale(actor, 0.01f);")]),
]

ATTACKS = [
    dict(part="Sword hitbox", shape="two quads from the hand to the blade tip, only while a swing is active",
         reach_from_hand=dict(master_sword=40, kokiri_sword=30, biggorons_sword=55, megaton_hammer=25,
                              deku_stick="varies with how much of the stick is left"),
         note=("model lengths 4000 / 3000 / 5500 / 2500 x 0.01. The quads are rebuilt each frame from the hand "
               "position, so the area they sweep follows the swing animation"),
         src=[(PLIB, "4000.0f, // Master Sword"), (PLIB, "3000.0f, // Kokiri Sword"),
              (PLIB, "5500.0f, // Biggoron's Sword"), (PLIB, "2500.0f, // Hammer")]),
    dict(part="Shield", shape="quad in front of the hand (held) or on the back (stowed)",
         size="held: about 60 x 60 world units (model -4500..1500 x -3000..3000); on the back: 60 x 60",
         note="it blocks (AC_HARD) and can also hit (AT). Its material depends on the equipped shield",
         src=[(PLIB, "{ -4500.0f, -3000.0f, -600.0f },"), (P, "AC_ON | AC_HARD | AC_TYPE_ENEMY,")]),
]

COLLISION_ENGINE = dict(
    order=["wall check (line from last position to new position at feet + 26, then sphere push-out)",
           "ceiling check", "floor ray cast (from last height + 50)", "water check"],
    how_walls_work=("Walls are tested at ONE height: feet + 26 (15 crawling). A line from last frame's position to "
                    "this frame's catches fast movement, then a sphere of the wall-check radius pushes Link out along "
                    "the wall's normal. Geometry entirely below that height is not a wall to Link: the floor ray (cast "
                    "from 50 above) lets him walk up onto it."),
    clip_conditions=[
        dict(condition="Fast falling",
             effect=("if this frame's downward movement is more than 21 units (26 + dy < 5), the wall line test runs "
                     "at foot height instead of feet + 26; the decomp marks this as a bug"),
             src=[(BG, "//! @bug checkHeight is not applied to posPrev/posNext")]),
        dict(condition="Collision grid cell edges",
             effect=("the sphere push-out only searches the nearest static collision grid cell, so walls in a "
                     "neighbouring cell can be missed (the decomp flags this as a possible bug)"),
             src=[(BG, "// possible bug? if the sphere's radius is smaller than the distance to a subdivision boundary, some static")]),
        dict(condition="Low geometry",
             effect="anything that doesn't reach feet + 26 never blocks Link; he steps onto it if its top is within 50 of his last height",
             src=[(P, "vWallCheckHeight = 26.0f;"), (ACT, "pos->y += 50.0f;")]),
        dict(condition="Squeezed between floor and ceiling",
             effect="if a ceiling is hit and the floor is more than 15 above Link, he is flagged as crushed",
             src=[(ACT, "if (floorHeightDiff > 15.0f) {")]),
        dict(condition="Moving platforms and actor walls",
             effect="checked separately from level geometry (dynamic polygons), then re-checked with a one-sided line test",
             src=[(BG, "if (BgCheck_SphVsDynaWall(colCtx, xpFlags, &posResult->x, &posResult->z, &sphCenter, radius, outPoly, outBgId,")]),
    ],
    community_note=("Speedrun clips (seam walks, hovering through walls, superslide clips and so on) work through these "
                    "conditions. The specific setups are community knowledge and aren't verified here."),
)

TICK = dict(
    rate="20 game frames per second (NTSC). Each frame:",
    frame_order=[
        "1. Room changes are processed",
        ("2. Collision is resolved: attacks vs hurtboxes (AT/AC), actors pushing each other (OC), damage. This uses "
         "the colliders every actor registered DURING THE PREVIOUS FRAME"),
        ("3. Every actor updates, by category: switches, moving platforms (BG), Link, explosives, NPCs, enemies, "
         "props, item actors, misc, bosses, doors, chests"),
        "4. Cutscenes, effects, camera, text boxes and the HUD update",
    ],
    link_update_order=[
        "1. Targeting (Z) and HUD state",
        "2. Movement: last frame's speed + gravity -> new position -> wall, ceiling, floor and water checks",
        "3. Loading zones and void-outs",
        "4. Ledge, fall and auto-jump checks",
        "5. Stick and buttons are read; the current action decides the new speed, direction or jump",
        "6. Hurtbox and sword/shield hitboxes are rebuilt and registered for the next frame's collision check",
    ],
    consequences=[
        "An input on frame N first moves Link on frame N+1 (movement runs before the action in Link's update)",
        "A sword hitbox registered on frame N hits on frame N+1; the enemy reacts in its own update on frame N+1",
        "Moving platforms update before Link, so he rides their new position on the same frame",
        "Enemies, switches and platforms freeze while Link is talking (and in a few other states); NPCs keep updating",
    ],
    src=[(PLAY, "CollisionCheck_AT(this, &this->colChkCtx);"), (PLAY, "Actor_UpdateAll(this, &this->actorCtx);"),
         (PROF, "/* 0x01 */ ACTORCAT_BG,"), (ACT, "u32 sCategoryFreezeMasks[ACTORCAT_MAX] = {"),
         (P, "Player_ProcessControlStick(play, this);")],
)
