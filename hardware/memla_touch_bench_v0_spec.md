# Memla Touch Bench V0 Hardware Spec

Last updated: 2026-07-11

## Goal

Build the fastest possible physical proof that Memla can use a real phone without OS integration.

V0 is not the final beautiful case/earpiece. V0 is a bench rig:

```text
fixed phone dock
+ overhead camera
+ XY gantry
+ soft conductive stylus Z tapper
+ Memla software
= phone can be operated by coordinates like a human finger
```

The V0 target is:

- Touch any visible point on one fixed phone.
- Support tap, long press, simple swipe.
- Use camera/screenshot/AltStore browser state for perception.
- Verify every action by visual or instrumented state delta.
- Never tap final payment/send/request/delete without explicit human confirmation.
- Generate physical-touch transmutation traces for the meta fortress.

## Recommended Build Strategy

Use the current AltStore/WKWebView DoorDash work as the instrumented gym, but force every action to become:

```text
semantic target -> bounds -> safe tap coordinate -> physical tap -> post-touch verifier
```

Do not jump directly to native apps or pure camera-only vision. First clear these lanes:

1. `instrumented_web`: DOM + bounds + JS fallback available.
2. `instrumented_web_physical`: DOM/bounds used only to choose physical coordinates.
3. `mobile_browser_physical`: screenshot/OCR + physical touch.
4. `native_app_physical`: accessibility/OCR + physical touch.
5. `dock_remote`: phone at home, earpiece/PC/wearable controls dock over encrypted tunnel.

## Cost Summary

These are practical US planning numbers, not guaranteed checkout prices.

| Build | What It Is | Cost If You Already Have A Computer | Cost With Dedicated Mini PC |
|---|---|---:|---:|
| V0-Cheap | Generic XY plotter/laser frame, webcam, stylus | `$280-$550` | `$430-$800` |
| V0-Recommended | Better frame/rails, 4K camera, proper Z compliance | `$550-$950` | `$700-$1,200` |
| V0-Low Mechanical Risk | OpenBuilds ACRO Draw Bot + SCRIBE lifter | `$950-$1,300` | `$1,100-$1,650` |

If you have an old 3D printer, you can prototype for `$60-$180` by mounting a stylus in place of the toolhead, but it is clumsy and slower.

## V0-Recommended BOM

### Motion System

Pick one.

#### Option A: Generic XY Plotter / Laser Engraver Frame

Use a small 300x300mm or 400x400mm belt-driven XY frame. Remove laser/pen if included and mount a capacitive stylus.

Expected cost: `$180-$350`.

Requirements:

- At least 120mm x 240mm usable motion.
- NEMA17 steppers preferred.
- GRBL-compatible controller preferred.
- Belt drive is fine.
- Repeatability target: within 1.5mm.
- Absolute accuracy target after calibration: within 3mm.

This is the best cost/speed V0.

#### Option B: OpenBuilds ACRO Draw Bot

More expensive, less mechanical guesswork.

- OpenBuilds A1 ACRO Draw Bot: listed at `$759.99`.
- OpenBuilds SCRIBE Pen Lifter: listed at `$39.99`.

This is overkill for a phone, but reliable and clean. Use it if you want to spend money to reduce mechanical debugging.

### Z Tapper

The Z axis is the most important part. Do not rigidly slam the screen.

Minimum:

- Micro servo or pen lifter: `$10-$40`.
- Spring-compliant stylus holder: `$5-$25`.
- Soft conductive capacitive stylus tip: `$8-$15`.

Better:

- Dedicated pen lifter / servo lifter: `$40-$80`.
- Adjustable spring preload.
- Physical down-stop so force cannot exceed safe range.

Target force:

- Start around `40-60g`.
- Stay below `120g`.
- Never exceed `150g`.

Calibrate with a cheap kitchen scale. Lower stylus onto scale, command tap-down, adjust servo/down-stop until the scale reads in range.

### Stylus

Use passive capacitive stylus tips first.

Buy:

- Mesh or rubber capacitive stylus pack: `$8-$15`.
- Copper tape: `$6-$10`.
- 1M ohm resistors: `$5`.
- Thin flexible wire: `$5`.

Important: many capacitive stylus tips work better when referenced to ground/body capacitance.

Safe V0 wiring:

```text
stylus conductive shaft/tip backing
-> copper tape/wire
-> 1M ohm resistor
-> controller/USB ground
```

Do not inject voltage into the phone screen. The stylus should be passive/conductive, not powered.

If the phone does not register taps:

1. Increase conductive surface area behind the tip.
2. Ground through 1M ohm resistor.
3. Use a larger 6-8mm mesh tip.
4. Lower slightly more force.
5. Try a different tempered-glass screen protector.

### Camera

Minimum:

- 1080p USB webcam: `$25-$70`.

Recommended:

- 4K USB webcam: `$80-$170`.

Why 4K matters: phone text/buttons are small. You can downsample, but the extra pixels help OCR and bounds validation.

Good-enough choices:

- Obsbot Meet SE style 1080p webcam: roughly `$58` deal pricing reported in 2026.
- Logitech Brio / MX Brio style 4K webcam: roughly `$120-$170`; Brio sale pricing was reported around `$149.99`.

Mounting:

- Camera height: `250-400mm` above screen.
- Lens angle: as close to perpendicular as possible.
- Rigid mount, no wobble.
- Add diffuse light if screen glare hurts OCR.

### Phone Dock

Cost: `$20-$80`.

Requirements:

- Rigid slot for one target phone.
- Phone cannot move during a run.
- Charger access.
- Screen fully visible.
- Case/screen protector allowed.
- Repeatable insertion position.

Recommended:

- 3D printed cradle or laser-cut acrylic plate.
- Four side stops: left, right, bottom, top.
- Rubber pads to avoid scratches.
- Optional MagSafe/Qi charger.

Do not rely on a loose desk stand.

### Electronics

If your XY frame includes a controller, use it.

If DIY:

- Arduino Uno clone or Nano-compatible controller: `$10-$25`.
- CNC Shield V3 or GRBL controller: `$10-$25`.
- 2x stepper drivers, A4988 minimum / TMC2209 better: `$10-$35`.
- 2x NEMA17 steppers: `$25-$45`.
- 12V 5A power supply: `$15-$25`.
- Limit switches: `$5-$15`.
- Servo/pen lifter power: 5V 2A supply or buck converter: `$8-$15`.
- Emergency stop switch: `$8-$20`.
- Wiring/connectors: `$15-$40`.

Grounds:

- Controller ground and servo ground common.
- Stylus ground through high-value resistor only.
- Keep motor power and USB stable; motor noise can reset cheap controllers.

### Compute

Use what you already have first.

Recommended V0 compute:

- Existing PC/Mac/Linux laptop or your server.
- USB camera plugged into compute.
- USB serial to motion controller.
- Memla runs locally or connects to your stronger server.

Dedicated compute options:

- Used mini PC / Intel N100 class box: `$120-$250`.
- Raspberry Pi can run camera/control, but not local 7B well; Pi pricing has also been volatile.

Best architecture:

```text
mini PC / laptop:
  camera capture
  touchd actuator daemon
  OpenCV calibration
  Memla adapter

server / main PC:
  local model
  transmutation bank
  meta fortress
```

### Audio / Earpiece

V0 does not need custom earpiece hardware.

Start with:

- Any Bluetooth headset / AirPods / wired earbuds: `$30-$180`.
- ASR/TTS through laptop/phone/server.

V0 audio goal:

- User speaks task.
- Memla confirms briefly.
- Memla executes on phone dock.
- Memla reads concise status.

Do not do remote phone-call audio relay in V0. That is V1/V2.

## Mechanical Layout

Top view:

```text
+------------------------------------------------+
| XY gantry frame                                |
|                                                |
|       camera                                   |
|        |                                       |
|        v                                       |
|   +-----------+                                |
|   |  phone    |                                |
|   |  screen   |  <- fixed cradle               |
|   +-----------+                                |
|                                                |
| stylus carriage moves over screen              |
+------------------------------------------------+
```

Side view:

```text
camera
  |
  v
stylus carriage ---- Z lifter
                     |
                     v
                 soft stylus tip
                 phone glass
```

Keep the stylus parked away from the screen when idle.

## Coordinate Contract

Memla should never command raw motor steps directly.

Canonical action:

```json
{
  "action_type": "tap",
  "target_id": "dd_add_to_cart",
  "target_label": "Add to cart",
  "bounds_norm": {"x": 0.08, "y": 0.82, "w": 0.84, "h": 0.08},
  "safe_point_norm": {"x": 0.50, "y": 0.86},
  "coordinate_confidence": 0.94,
  "safety": "safe",
  "force_limit_g": 80,
  "expected_delta": "cart drawer visible"
}
```

The touch adapter converts:

```text
normalized screen coordinate -> camera pixel -> actuator millimeters -> GRBL position
```

Store all three coordinate systems in traces:

```json
{
  "screen_norm": {"x": 0.5, "y": 0.86},
  "camera_px": {"x": 1210, "y": 1720},
  "actuator_mm": {"x": 52.3, "y": 148.7}
}
```

## Software Daemon: `touchd`

Build a tiny local daemon that owns physical control.

Minimum endpoints:

```text
GET  /health
GET  /frame
POST /calibrate
POST /tap
POST /long_press
POST /swipe
POST /park
POST /kill
```

Example commands:

```json
POST /tap
{
  "x_norm": 0.52,
  "y_norm": 0.84,
  "force_limit_g": 80,
  "duration_ms": 90,
  "expected_delta": "cart drawer visible",
  "safety": "safe"
}
```

```json
POST /swipe
{
  "x1_norm": 0.55,
  "y1_norm": 0.78,
  "x2_norm": 0.55,
  "y2_norm": 0.35,
  "duration_ms": 450,
  "safety": "safe"
}
```

The daemon must reject:

- out-of-screen coordinates
- unknown calibration
- low coordinate confidence
- boundary actions
- repeated blind taps
- kill switch active
- phone moved since calibration

## Calibration

### 1. Camera-to-Screen Calibration

Detect the phone screen rectangle in the camera image.

V0 manual method:

1. Show white screen on phone.
2. Capture frame.
3. User clicks four screen corners in calibration UI.
4. Compute homography.

Store:

```json
{
  "camera_px_corners": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
  "screen_norm_corners": [[0,0], [1,0], [1,1], [0,1]]
}
```

### 2. Actuator-to-Screen Calibration

Manual method:

1. Move stylus to visible screen center.
2. Adjust until it lands at center.
3. Repeat for four corners.
4. Fit affine/homography from screen normalized coordinates to actuator mm.

Better method:

1. Open calibration page in Memla Browser.
2. Display large crosshair targets.
3. Actuator taps target.
4. Page logs actual touch point.
5. Compute correction automatically.

### 3. Force Calibration

Use kitchen scale:

1. Put scale under stylus.
2. Command tap down.
3. Adjust Z down-stop until scale reads `40-80g`.
4. Record servo pulse width or Z position.
5. Hard-limit maximum to under `150g`.

### 4. Drift Check

Before every run:

- Capture phone screen rectangle.
- Compare corners against last calibration.
- If moved more than `2mm` equivalent, recalibrate.

## Action Timing

Initial conservative timings:

- Move to target: `200-600ms`.
- Tap down: `60-120ms`.
- Tap up: immediate.
- Post-tap wait: `500-1200ms`.
- Verify frame delta: `200-500ms`.

Target mature speed:

- Known safe tap: `0.5-1.0s`.
- Known flow action including verification: `1.0-2.0s`.
- DoorDash known flow: `45-120s`, app/network dependent.

## Safety Gates

Hardware gates:

- Emergency stop cuts motor/servo power.
- Software kill endpoint.
- Servo down-stop prevents high force.
- Stylus is soft and conductive, not metal point.
- Phone has tempered glass screen protector.
- Motors park stylus off-screen when idle.

Software gates:

- No action if calibration invalid.
- No tap if target bounds are missing.
- No tap if safe point is within `6mm` of boundary/neighbor target.
- No tap if target label matches final boundary terms:
  - place order
  - pay now
  - send
  - request ride
  - confirm purchase
  - delete
  - submit
- No repeated blind tap after no visible delta.
- Always re-inspect after action.

Boundary behavior:

```text
reach checkout/send/request screen
verify desired state
speak "Ready for you to confirm"
park stylus
wait for human
```

## Memla Fortress Changes

Add a physical-touch adapter below the agency fortress.

New trace fields:

```json
{
  "perception_lane": "instrumented_web_physical",
  "screen_evidence": ["visible label", "bounds", "OCR"],
  "touch_target": {
    "label": "Add to cart",
    "bounds_norm": {"x": 0.08, "y": 0.82, "w": 0.84, "h": 0.08},
    "safe_point_norm": {"x": 0.50, "y": 0.86},
    "neighbor_risk": "low",
    "coordinate_confidence": 0.94
  },
  "physical_action": {
    "type": "tap",
    "force_limit_g": 80,
    "duration_ms": 90
  },
  "post_touch_verifier": ["cart drawer visible", "button state changed"]
}
```

New confusion classes:

- `coordinate_uncertainty`
- `target_occluded`
- `neighbor_collision_risk`
- `screen_moved_after_calibration`
- `post_touch_no_delta`
- `visual_ocr_ambiguous`
- `boundary_button_too_close`
- `keyboard_overlay_changed_layout`
- `capacitive_touch_not_registered`

## First Demo Milestones

### Milestone 1: Physical Tap Hello World

Goal:

- Open a simple local web page with four big buttons.
- Memla selects each by coordinate.
- 20/20 taps register.

Pass:

- `>= 95%` tap success.
- No off-target taps.
- Average tap+verify under `2s`.

### Milestone 2: Memla Browser Physical Mode

Goal:

- Current AltStore browser extracts DoorDash candidates and bounds.
- Memla uses physical tapper instead of JS tap.

Pass:

- Open DoorDash web.
- Search/open Domino's.
- Tap item card.
- Tap Large.
- Add to cart.
- Stop before payment.

### Milestone 3: Quantity Fortress

Goal:

- Prompt: "two large cheese pizzas from Dominos, stop before payment."
- Memla must find quantity control or duplicate item/cart quantity path.

Pass:

- Cart/checkout shows quantity 2.
- No payment submitted.
- No teacher call during run after bank is loaded.

### Milestone 4: Safari / Real Browser

Goal:

- Same flow without WKWebView DOM truth.
- Use screenshot/OCR/candidate inference.

Pass:

- `70%+` on 20 DoorDash/Uber Eats tasks.
- No boundary violations.

### Milestone 5: Native App Transfer

Goal:

- Same constraint families on DoorDash/Uber Eats native apps.

Pass:

- `60%+` early transfer.
- Failure traces become micro-fortresses.

## Exact Build Order

1. Buy or assemble XY frame.
2. Install GRBL or vendor motion controller.
3. Verify `G0 X Y` movement.
4. Mount phone cradle rigidly.
5. Mount camera rigidly.
6. Mount stylus with spring compliance.
7. Add Z lifter.
8. Add emergency stop.
9. Calibrate force with kitchen scale.
10. Calibrate camera screen rectangle.
11. Calibrate actuator coordinate map.
12. Run tap tests on a blank grid page.
13. Run tap tests on Memla Browser big buttons.
14. Integrate `touchd`.
15. Run DoorDash web physical tap lane.
16. Record every failure as a fortress confusion.

## Shopping List: Recommended V0

Assuming you already have a computer:

| Item | Cost |
|---|---:|
| Generic XY plotter / laser frame | `$180-$350` |
| Z pen lifter / micro servo assembly | `$15-$60` |
| Capacitive stylus tips + copper tape + resistor | `$20-$35` |
| 1080p/4K USB camera | `$60-$160` |
| Phone cradle materials / 3D print / acrylic | `$20-$80` |
| Emergency stop + wiring + misc hardware | `$40-$90` |
| Lighting / diffuser | `$15-$40` |
| Tempered glass screen protectors | `$10-$25` |
| Total | `$360-$840` |

If buying OpenBuilds reliability:

| Item | Cost |
|---|---:|
| OpenBuilds A1 ACRO Draw Bot | `$759.99` |
| OpenBuilds SCRIBE Pen Lifter | `$39.99` |
| Stylus/grounding parts | `$20-$35` |
| USB camera | `$60-$160` |
| Phone cradle/mounting | `$40-$100` |
| Emergency stop/misc | `$40-$90` |
| Total | `$960-$1,185` |

Add `$120-$250` if you want a dedicated mini PC.

## What Not To Build In V0

Do not build:

- custom earpiece
- cellular relay
- Bluetooth call bridge
- active capacitive screen protector
- beautiful case shell
- native-app-only vision path

Those are later. V0 exists to prove:

```text
Memla can physically operate a real phone from constraints and verification.
```

## V0 Success Definition

The V0 is real when it can run this uncherry-picked:

```text
20 DoorDash/Memla Browser runs
target: large cheese pizza from Domino's
mutations: toppings, quantity, cart verification
terminal: checkout/review state
boundary: no payment/order submission
teacher: off
```

Pass line:

- `>= 85%` reaches correct safe review state.
- `0` irreversible boundary violations.
- `<= 1` blind-repeat tap per run, ideally `0`.
- every failure emits a confusion signal for the meta fortress.

That proves the hardware wedge is worth turning into a product body.
