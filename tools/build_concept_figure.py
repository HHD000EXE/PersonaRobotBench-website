#!/usr/bin/env python3
"""Build the concept SVGs from one grid and the Task 1 layout coordinates.

No rendering dependencies are required. A/B connectors share the same geometry;
all before views reuse one SVG symbol. Keyboard and monitor remain fixed.
"""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, LINE = "#17243b", "#607087", "#dce3ed"
BLUE, TEAL = "#2459a9", "#386c72"
PALES = ("#edf3fc", "#edf5f5")
COLORS = (BLUE, TEAL)
FIGURE_TITLE = "Same Instruction, Different User Personas: Personalized Robot Actions."
USER_INSTRUCTION = "“Set up my desk for work.”"
INITIAL = {"mouse": (0, .06), "notebook": (-.34, .09)}
FINAL = [
    {"mouse": (-.32, -.12), "notebook": (.35, -.12)},
    {"mouse": (.32, -.12), "notebook": (-.35, -.12)},
]


def text(x, y, value, size=16, fill=INK, weight=400, anchor="start", **attrs):
    extra = " ".join(f'{k.replace("_", "-")}="{escape(str(v))}"' for k, v in attrs.items())
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}" {extra}>{escape(value)}</text>')


def rect(x, y, w, h, fill="#fff", stroke=LINE, rx=10, **attrs):
    extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" {extra}/>'


def path(d, color=MUTED, width=2, **attrs):
    extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round" {extra}/>')


def arrow(x1, y1, x2, y2, color, marker, **attrs):
    return path(f"M{x1} {y1} L{x2} {y2}", color, 2,
                marker_end=f"url(#{marker})", **attrs)


def avatar(x, y, color, pale, scale=1):
    return (f'<g transform="translate({x} {y}) scale({scale})">'
            f'<circle r="21" fill="{pale}"/><circle cy="-5" r="6.5" fill="{color}"/>'
            + path("M-11 12 Q-10 3 0 3 Q10 3 11 12", color, 4.5) + "</g>")


def brain(x, y, scale=1):
    return (f'<g transform="translate({x} {y}) scale({scale})">'
            '<circle r="24" fill="#fff" stroke="#dce3ed"/>'
            + path("M-8 12 V6 Q-17 2-13-7 Q-11-17 0-17 Q14-17 14-3 L18 4 H12 V12 H4", "#587193", 2)
            + path("M-7-3 H3 M-2-8 V2", BLUE, 2)
            + f'<circle cx="5" cy="-6" r="2" fill="{TEAL}"/></g>')


def robot(x, y, scale=1):
    return (f'<g transform="translate({x} {y}) scale({scale})">'
            + path("M-17 81 -20 126 M17 81 20 126", INK, 13)
            + path("M-29 128 -14 128 M14 128 29 128", INK, 9)
            + rect(-32, 14, 64, 73, "#f4f7fc", INK, 18)
            + rect(-23, -30, 46, 36, "#fff", INK, 12)
            + rect(-16, -20, 32, 15, INK, "none", 6)
            + '<circle cx="-8" cy="-13" r="2.3" fill="#85b0ed"/>'
            + '<circle cx="8" cy="-13" r="2.3" fill="#85b0ed"/>'
            + path("M0-37 V-31", INK, 3)
            + f'<circle cy="-40" r="3" fill="{BLUE}"/>'
            + path("M-33 28 -49 56 -38 75 M33 28 49 56 39 75", INK, 10)
            + '<circle cx="-38" cy="76" r="7" fill="#fff" stroke="#17243b"/>'
            + '<circle cx="39" cy="76" r="7" fill="#fff" stroke="#17243b"/>'
            + rect(-17, 28, 34, 24, "#e8eef7", "none", 7)
            + path("M-8 40 H8", BLUE, 3) + "</g>")


def mouse(x, y, color, scale=1):
    return (f'<g transform="translate({x} {y}) scale({scale})">'
            + rect(-6, -11, 12, 22, "#fff", color, 5)
            + path("M-5-3 H5 M0-10 V-3", color, 1)
            + rect(-.8, -8, 1.6, 3.5, color, "none", .8) + "</g>")


def notebook(x, y, color, scale=1):
    return (f'<g transform="translate({x} {y}) scale({scale})">'
            + rect(-10, -14, 20, 28, "#fff", color, 2)
            + path("M-6-13 V13 M-2-7 H6 M-2-1 H6 M-2 5 H6", color, .8)
            + path("M-8-9 H-12 M-8-3 H-12 M-8 3 H-12 M-8 9 H-12", color, 1.2)
            + "</g>")


def keyboard(x, y, scale=1):
    s = f'<g transform="translate({x} {y}) scale({scale})">' + rect(-24, -8, 48, 16, "#e9edf3", "#8c9cb0", 2)
    for yy in (-4, 0):
        for xx in range(-19, 20, 6):
            s += rect(xx, yy, 4, 2.5, "#b3becd", "none", .4)
    return s + rect(-11, 4, 22, 2, "#b3becd", "none", .4) + "</g>"


def monitor(x, y, scale=1):
    return (f'<g transform="translate({x} {y}) scale({scale})">'
            + rect(-24, -8, 48, 16, "#edf1f6", "#8c9cb0", 2)
            + path("M0 9 V13 M-8 13 H8", "#8c9cb0", 1.4) + "</g>")


def desk_symbol(name, positions, color):
    """Task 1 XY relations; object labels belong to the illustration itself."""
    s = f'<g id="{name}">' + rect(1, 1, 154, 126, "#fff", LINE, 7)
    s += monitor(78, 70 - 140 * .29)
    s += keyboard(78, 70 - 140 * -.12)
    for obj, (xx, yy) in positions.items():
        stroke = color if obj == "mouse" else "#687b92"
        s += (mouse if obj == "mouse" else notebook)(78 + 144 * xx, 70 - 140 * yy, stroke)
    s += text(78, 13, "Monitor · fixed", 7.5, MUTED, anchor="middle")
    s += text(78, 110, "Keyboard · fixed", 7, MUTED, anchor="middle")
    mx, my = positions["mouse"]
    nx, ny = positions["notebook"]
    if name == "desk-before":
        s += path("M86 62 H93", MUTED, .8)
        s += text(96, 65, "Mouse", 8.5, MUTED)
        s += text(29, 83, "Paper", 8, MUTED, anchor="middle")
        s += text(29, 93, "notebook", 8, MUTED, anchor="middle")
    else:
        s += text(78+144*mx, 111, "Mouse", 8.5, color, 600, "middle")
        s += text(78+144*nx, 112, "Paper", 7.5, MUTED, anchor="middle")
        s += text(78+144*nx, 122, "notebook", 7.5, MUTED, anchor="middle")
    return s + "</g>"


def use_desk(name, x, y, scale=1):
    return f'<use href="#{name}" transform="translate({x} {y}) scale({scale})"/>'


def definitions():
    s = "<defs>"
    for name, color in [("arrowA", BLUE), ("arrowB", TEAL), ("arrowGray", MUTED)]:
        s += (f'<marker id="{name}" viewBox="0 0 10 10" refX="8" refY="5" '
              'markerWidth="4" markerHeight="4" orient="auto">'
              f'<path d="M1 1 9 5 1 9" fill="none" stroke="{color}" stroke-width="1.8" '
              'stroke-linecap="round" stroke-linejoin="round"/></marker>')
    s += desk_symbol("desk-before", INITIAL, "#687b92")
    for i, color in enumerate(COLORS):
        s += desk_symbol("desk-after-" + str(i), FINAL[i], color)
    return s + "</defs>"


def document(w, h, body, mobile=False):
    description = ("Two users provide profiles containing only a dominant-hand attribute and give the identical "
                   "instruction, Set up my desk for work. One personal robot policy reads the profile, instruction "
                   "and scene, infers a task-relevant persona that prioritizes computer use, plans and executes. "
                   "The policy connects its inferred plan directly to a small robot on each Before-to-After transition. The robot places the mouse on the user's dominant-hand side. The paper notebook is shown "
                   "set aside to keep the workspace clear in this illustrative arrangement. "
                   "Both before views reuse the same Task 1 initial desk state; the keyboard and monitor stay fixed. "
                   "Object labels are integrated into each desk view. Held-out user preferences go only to evaluation. "
                   "This is a conceptual mouse-layout illustration, not a measured rollout result.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            'role="img" aria-labelledby="concept-title concept-desc">\n'
            f'<title id="concept-title">{escape(FIGURE_TITLE)}</title>\n'
            f'<desc id="concept-desc">{escape(description)}</desc>\n' + definitions()
            + f'<g font-family="Arial, Helvetica, sans-serif">{rect(0, 0, w, h, "#fff", "none", 0)}'
            + body + "</g></svg>\n")


def execution_robot(cx, cy, color, lane, scale=.38, radius=41, label_inside=False):
    # Keep the action label inside desktop hubs, clear of central branch arrows.
    icon_y = cy - 44 * scale - (8 if label_inside else 0)
    s = (f'<g data-node="execution" data-lane="{lane}">'
         + f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="#fff" stroke="{color}" stroke-opacity=".25"/>'
         + robot(cx, icon_y, scale))
    if label_inside:
        s += text(cx, cy+31, "Plan & act", 11, INK, 600, "middle")
    return s + "</g>"


def desktop():
    s = text(28, 35, "PERSONALIZATION STARTS WITH THE USER", 11, BLUE, 700, letter_spacing=1.6)
    s += text(28, 78, FIGURE_TITLE, 32, weight=600, letter_spacing=-.7)
    s += text(28, 109, "The shared policy infers a user-specific plan and connects it directly to robot execution.", 16, MUTED)
    for x, title in [(28, "USER PROFILE + SAME INSTRUCTION"), (312, "SHARED ROBOT POLICY / PLANNER"),
                     (584, "EXECUTE THE PLAN: BEFORE → AFTER")]:
        s += text(x, 143, title, 11, MUTED, 700, letter_spacing=.4)
    s += rect(312, 164, 236, 528, "#f7f9fc", LINE, 12, data_stage="policy")
    s += text(430, 198, "Infer persona & plan", 18, weight=600, anchor="middle")
    s += text(430, 223, "Profile + instruction + scene", 12, MUTED, anchor="middle")
    s += brain(430, 417)
    s += text(430, 466, "Plans tailored to each user", 13, MUTED, anchor="middle")
    s += text(430, 668, "Same policy for both users", 13, MUTED, 600, "middle")
    desk_scale = 15 / 13  # 180px desk views, centered around the execution node.

    for i, y in enumerate((164, 442)):
        color, pale, letter = COLORS[i], PALES[i], "AB"[i]
        cy = y + 125
        hand = ("left", "right")[i]
        s += rect(28, y, 248, 250, "#fff", color, 12, stroke_opacity=.28)
        s += path(f"M29 {y+18} V{y+232}", color, 3)
        s += avatar(65, y+37, color, pale, .82)
        s += text(96, y+41, "USER " + letter, 16, color, 700)
        s += text(48, y+79, "DOMINANT HAND", 11, MUTED, 600, letter_spacing=.45)
        s += text(48, y+119, hand.capitalize(), 30, color, 600)
        s += rect(48, y+151, 208, 22, "#e9eef6", "none", 4)
        s += text(152, y+166, "IDENTICAL INSTRUCTION", 10.5, INK, 700, "middle", letter_spacing=.3)
        s += text(152, y+216, USER_INSTRUCTION, 16, weight=500, anchor="middle", data_field="instruction")
        s += rect(328, cy-49, 204, 98, pale, "none", 9)
        s += text(343, cy-24, f"{letter} · INFERRED TASK PERSONA", 9, color, 700)
        s += text(343, cy+1, "Computer work first", 13, MUTED)
        s += text(343, cy+29, f"Mouse → {hand} side", 15, color, 600)
        s += rect(584, y, 588, 250, pale, "none", 12)
        s += text(690, y+36, "Before", 14, MUTED, 600, "middle")
        s += text(1066, y+36, "After · User " + letter, 14, color, 600, "middle")
        s += use_desk("desk-before", 600, cy - 64*desk_scale, desk_scale)
        s += use_desk("desk-after-" + str(i), 976, cy - 64*desk_scale, desk_scale)
        s += arrow(282, cy, 306, cy, color, "arrow"+letter,
                   data_connector="profile-policy", data_lane=letter)
        s += execution_robot(878, cy, color, letter, .28, 41, label_inside=True)
        s += arrow(788, cy, 829, cy, MUTED, "arrowGray",
                   data_connector="before-execution", data_lane=letter)
        s += arrow(927, cy, 968, cy, color, "arrow"+letter,
                   data_connector="execution-after", data_lane=letter)
        s += text(600, y+18, "Top-down · user at bottom", 9.5, MUTED)
        s += text(1066, y+242, f"Mouse on the dominant {hand} side", 11, color, 500, "middle")
        s += f'<circle cx="312" cy="{cy}" r="3.5" fill="{color}"/>'
    # A single shared planner output reaches the midpoint, then splits by user.
    s += path("M554 428 H716 H878", MUTED, 2, marker_mid="url(#arrowGray)", data_connector="planner-trunk")
    s += '<circle cx="548" cy="428" r="3.5" fill="#607087"/>'
    s += '<circle cx="878" cy="428" r="3.5" fill="#607087"/>'
    for i, target_y in enumerate((338, 518)):
        s += arrow(878, 428, 878, target_y, COLORS[i], "arrow"+"AB"[i],
                   data_connector="planner-execution", data_lane="AB"[i])
    s += text(878, 713, "Same robot and policy · two user-conditioned executions", 12, MUTED, anchor="middle")
    for x, title, subtitle in [
        (28, "Held-out user preferences", "Used only for evaluation"),
        (440, "Evaluate personalization", "Does the behavior fit this user?"),
        (852, "Robot-side evidence", "Inferred persona + execution"),
    ]:
        s += rect(x, 724, 320, 68, "#f7f9fc", LINE, 10)
        s += text(x+160, 751, title, 15, weight=600, anchor="middle")
        s += text(x+160, 774, subtitle, 12, MUTED, anchor="middle")
    s += arrow(356, 758, 432, 758, MUTED, "arrowGray", stroke_dasharray="4 4")
    s += arrow(844, 758, 768, 758, MUTED, "arrowGray", stroke_dasharray="4 4")
    s += text(28, 825, "Conceptual Task 1 mouse-layout example · Keyboard and monitor remain fixed.", 11, MUTED)
    return document(1200, 840, s)


def mobile():
    s = text(28, 24, "PERSONALIZATION STARTS WITH THE USER", 12, BLUE, 700, letter_spacing=.5)
    s += text(28, 64, "Same Instruction,", 30, weight=600, letter_spacing=-.5)
    s += text(28, 100, "Different User Personas:", 30, weight=600, letter_spacing=-.5)
    s += text(28, 136, "Personalized Robot Actions.", 30, weight=600, letter_spacing=-.5)
    s += rect(28, 156, 544, 310, "#fff", LINE, 12, data_stage="user-inputs")
    for i, x in enumerate((44, 326)):
        color, pale, letter = COLORS[i], PALES[i], "AB"[i]
        cx = x+115
        hand = ("left", "right")[i]
        s += rect(x, 172, 230, 146, pale, "none", 10)
        s += avatar(x+33, 208, color, pale, .75)
        s += text(x+66, 216, "USER " + letter, 23, color, 700)
        s += text(x+16, 252, "DOMINANT HAND", 18, MUTED, 600)
        s += text(x+16, 296, hand.capitalize(), 32, color, 600)
        s += arrow(cx, 474, cx, 506, color, "arrow"+letter,
                   data_connector="profile-policy", data_lane=letter)
    s += rect(44, 333, 512, 117, "#f7f9fc", "none", 9)
    s += text(300, 368, "IDENTICAL USER INSTRUCTION", 20, INK, 700, "middle")
    s += text(300, 414, USER_INSTRUCTION, 26, INK, 500, "middle", data_field="instruction")
    s += rect(28, 514, 544, 242, "#f7f9fc", LINE, 12, data_stage="policy")
    s += text(300, 552, "One robot policy: infer and plan", 27, weight=600, anchor="middle")
    s += text(300, 584, "Read profile + instruction + scene", 20, MUTED, anchor="middle")
    for i, x in enumerate((44, 326)):
        color, pale, letter = COLORS[i], PALES[i], "AB"[i]
        hand = ("left", "right")[i]
        s += rect(x, 605, 230, 127, pale, "none", 9)
        s += text(x+16, 635, letter + " · INFERRED PERSONA", 15.5, color, 700)
        s += text(x+16, 672, "Computer work first", 20, MUTED)
        s += text(x+16, 710, f"Mouse → {hand}", 26, color, 600)
    for i, x in enumerate((28, 310)):
        color, pale, letter = COLORS[i], PALES[i], "AB"[i]
        cx, hub_y = x+131, 1140
        s += rect(x, 804, 262, 676, pale, "none", 12)
        s += text(x+20, 842, "USER " + letter, 25, color, 700)
        s += text(cx, 877, "Before", 24, MUTED, 600, "middle")
        s += use_desk("desk-before", x+27, 892, 4/3)
        s += execution_robot(cx, hub_y, color, letter, .35, 36)
        s += arrow(cx, 1072, cx, 1096, MUTED, "arrowGray",
                   data_connector="before-execution", data_lane=letter)
        s += arrow(cx, 1184, cx, 1204, color, "arrow"+letter,
                   data_connector="execution-after", data_lane=letter)
        label_x = cx + (-43 if i else 43)
        label_anchor = "end" if i else "start"
        s += text(label_x, 1118, "Plan & act", 18, INK, 600, label_anchor)
        s += text(cx, 1233, "After", 24, color, 600, "middle")
        s += use_desk("desk-after-"+str(i), x+27, 1250, 4/3)
        s += text(cx, 790, "Top-down · user at bottom", 13, MUTED, 500, "middle")
    s += path("M300 764 V952 V1140", MUTED, 2, marker_mid="url(#arrowGray)", data_connector="planner-trunk")
    s += '<circle cx="300" cy="756" r="3.5" fill="#607087"/>'
    s += '<circle cx="300" cy="1140" r="3.5" fill="#607087"/>'
    s += arrow(300, 1140, 203, 1140, BLUE, "arrowA", data_connector="planner-execution", data_lane="A")
    s += arrow(300, 1140, 397, 1140, TEAL, "arrowB", data_connector="planner-execution", data_lane="B")
    s += text(300, 1513, "Same Unitree G1 and policy for both users", 20, MUTED, anchor="middle")
    s += rect(28, 1542, 262, 90, "#f7f9fc", LINE, 10)
    s += rect(340, 1542, 232, 90, "#f7f9fc", LINE, 10)
    s += text(48, 1573, "Held-out user", 23, weight=600)
    s += text(48, 1605, "preferences", 23, weight=600)
    s += arrow(298, 1587, 332, 1587, MUTED, "arrowGray", stroke_dasharray="4 4")
    s += text(456, 1574, "Evaluate", 27, weight=600, anchor="middle")
    s += text(456, 1606, "Persona + execution", 18, MUTED, anchor="middle")
    s += text(28, 1659, "Conceptual Task 1 desk-layout example.", 15, MUTED)
    return document(600, 1670, s, mobile=True)


def main():
    assets = ROOT / "assets"
    (assets / "persona-concept.svg").write_text(desktop(), encoding="utf-8")
    (assets / "persona-concept-mobile.svg").write_text(mobile(), encoding="utf-8")
    print("Built desktop 1200×840 and phone 600×1670 concept SVGs.")


if __name__ == "__main__":
    main()
