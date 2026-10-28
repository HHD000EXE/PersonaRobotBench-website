#!/usr/bin/env python3
"""Build the concept SVGs from one grid and the Task 1 layout coordinates.

No rendering dependencies are required. A/B connectors share the same geometry;
all before views reuse one SVG symbol. Only the mouse moves; other objects stay fixed.
"""
from html import escape
from pathlib import Path
from textwrap import wrap

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, LINE = "#17243b", "#607087", "#dce3ed"
BLUE, TEAL = "#2459a9", "#386c72"
PALES = ("#edf3fc", "#edf5f5")
COLORS = (BLUE, TEAL)
FIGURE_TITLE = "Same Instruction, Different User Personas: Personalized Robot Actions."
USER_INSTRUCTION = "“Set up my desk for work.”"
USER_NAMES = ("Mira", "Noah")
PROFILE_COMPONENTS = ("Background", "Living context", "Work", "Interests", "Habits")
USER_PROFILES = (
    (
        "Art-history graduate; now a museum researcher.",
        "Shares a compact apartment with a friend.",
        "Reviews archives and edits photos on a computer.",
        "Cycles on weekends and collects film cameras.",
        "Sketches and jots notes with her left hand.",
    ),
    (
        "Software engineer taking evening design classes.",
        "Lives with a partner and a rescue dog.",
        "Alternates between coding and online meetings.",
        "Bakes bread and repairs old radios.",
        "Annotates paper plans with his right hand.",
    ),
)
INITIAL = {"mouse": (0, .06), "notebook": (-.34, .09)}
FINAL = [
    {**INITIAL, "mouse": (-.32, -.12)},
    {**INITIAL, "mouse": (.32, -.12)},
]


def text(x, y, value, size=16, fill=INK, weight=400, anchor="start", **attrs):
    extra = " ".join(f'{k.replace("_", "-")}="{escape(str(v))}"' for k, v in attrs.items())
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}" {extra}>{escape(value)}</text>')


def profile_components(x, y, user, size=12.5, line_height=16, columns=34,
                       row_height=50, label_size=9.5, body_offset=17):
    # All components look alike: the policy must select relevant information.
    s = f'<g data-field="user-profile" data-user="{"AB"[user]}">'
    for i, (label, value) in enumerate(zip(PROFILE_COMPONENTS, USER_PROFILES[user])):
        yy = y + i * row_height
        lines = wrap(value, width=columns)
        spans = "".join(f'<tspan x="{x}" dy="{0 if j == 0 else line_height}">{escape(line)}</tspan>'
                        for j, line in enumerate(lines))
        s += f'<g data-component="{escape(label.lower().replace(" ", "-"))}">'
        s += text(x, yy, label.upper(), label_size, MUTED, 600, letter_spacing=.35)
        s += f'<text x="{x}" y="{yy+body_offset}" font-size="{size}" fill="{INK}">{spans}</text></g>'
    return s + "</g>"


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
    s += text(29, 36, "Notebook", 8, MUTED, anchor="middle")
    if name == "desk-before":
        s += path("M86 62 H93", MUTED, .8)
        s += text(96, 65, "Mouse", 8.5, MUTED)
    else:
        s += text(78+144*mx, 111, "Mouse", 8.5, color, 600, "middle")
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
    description = ("Conceptual workflow: two users provide profiles with personal background, living context, "
                   "work, interests and habits, and give the identical "
                   "instruction, Set up my desk for work. One personal robot policy reads the profile, instruction "
                   "and scene, selects task-relevant cues from the broader profile, infers likely preferences, "
                   "then plans and acts. The policy connects computer-based work and hand-use habits to this "
                   "desk instruction; relevance is not marked in the input profile. "
                   "The profiles do not provide a persona label, target mouse placement or explicit preference list. "
                   "Hand use during writing and sketching provides an illustrative cue for likely mouse-side preference; "
                   "it does not guarantee that preference. The inferred plan connects to the robot on each "
                   "Before-to-After transition. Both before views reuse the same initial desk state; "
                   "the keyboard, monitor and notebook stay fixed. The task persona setup goes only to evaluation, "
                   "never to the policy inputs. This conceptual Task 1 mouse-placement example does not depict "
                   "all task goals or a measured rollout result.")
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
    s += text(28, 109, "Full user profile → select task-relevant context → infer preferences → plan and act.", 16, MUTED)
    for x, title in [(28, "FULL USER PROFILE + SAME REQUEST"), (340, "SHARED ROBOT POLICY / PLANNER"),
                     (624, "EXECUTE THE PLAN: BEFORE → AFTER")]:
        s += text(x, 143, title, 11, MUTED, 700, letter_spacing=.25)
    s += rect(340, 164, 248, 796, "#f7f9fc", LINE, 12, data_stage="policy")
    s += text(464, 198, "Task-conditioned inference", 16, weight=600, anchor="middle")
    s += text(464, 223, "Full profile + instruction + scene", 12, MUTED, anchor="middle")
    s += brain(464, 520)
    s += text(464, 569, "Which context matters here?", 13, MUTED, anchor="middle")
    s += text(464, 599, "Relevance depends on the task", 11.5, MUTED, anchor="middle")
    s += text(464, 936, "Same policy for both users", 13, MUTED, 600, "middle")
    desk_scale = 15 / 13  # 180px desk views; one shared initial-desk symbol.

    for i, y in enumerate((164, 576)):
        color, pale, letter = COLORS[i], PALES[i], "AB"[i]
        cy = y + 192
        hand = ("left", "right")[i]
        s += rect(28, y, 276, 384, "#fff", color, 12, stroke_opacity=.28)
        s += path(f"M29 {y+18} V{y+366}", color, 3)
        s += avatar(65, y+36, color, pale, .82)
        s += text(96, y+40, USER_NAMES[i], 16, color, 700)
        s += profile_components(48, y+74, i)
        s += rect(48, y+326, 236, 22, "#e9eef6", "none", 4)
        s += text(166, y+341, "IDENTICAL INSTRUCTION", 10.5, INK, 700, "middle", letter_spacing=.3)
        s += text(166, y+371, USER_INSTRUCTION, 16, weight=500, anchor="middle", data_field="instruction")

        s += rect(356, cy-88, 216, 176, pale, "none", 9)
        s += text(372, cy-63, USER_NAMES[i].upper() + " · SELECT RELEVANT CUES", 9, color, 700)
        s += text(372, cy-39, "Computer work + hand-use habits", 11.5, INK)
        s += arrow(464, cy-25, 464, cy-10, color, "arrow"+letter,
                   data_connector="context-preference", data_lane=letter)
        s += text(372, cy+12, "INFER TASK PREFERENCE", 9, color, 700)
        s += text(372, cy+36, f"Likely {hand}-hand mouse use", 12, MUTED)
        s += text(372, cy+66, f"Plan: mouse → {hand} side", 15, color, 600)

        s += rect(624, y, 548, 384, pale, "none", 12)
        s += text(730, y+44, "Before", 14, MUTED, 600, "middle")
        s += text(1066, y+44, "After · " + USER_NAMES[i], 14, color, 600, "middle")
        s += use_desk("desk-before", 640, cy - 64*desk_scale, desk_scale)
        s += use_desk("desk-after-" + str(i), 976, cy - 64*desk_scale, desk_scale)
        s += arrow(310, cy, 334, cy, color, "arrow"+letter,
                   data_connector="profile-policy", data_lane=letter)
        s += execution_robot(898, cy, color, letter, .28, 41, label_inside=True)
        s += arrow(828, cy, 849, cy, MUTED, "arrowGray",
                   data_connector="before-execution", data_lane=letter)
        s += arrow(947, cy, 968, cy, color, "arrow"+letter,
                   data_connector="execution-after", data_lane=letter)
        s += text(640, y+25, "Top-down · user at bottom", 9.5, MUTED)
        s += text(1066, y+362, f"Mouse placed on the {hand} side", 11, color, 500, "middle")
        s += f'<circle cx="340" cy="{cy}" r="3.5" fill="{color}"/>'
    s += path("M594 562 H746 H898", MUTED, 2, marker_mid="url(#arrowGray)", data_connector="planner-trunk")
    s += '<circle cx="588" cy="562" r="3.5" fill="#607087"/>'
    s += '<circle cx="898" cy="562" r="3.5" fill="#607087"/>'
    for i, target_y in enumerate((405, 719)):
        s += arrow(898, 562, 898, target_y, COLORS[i], "arrow"+"AB"[i],
                   data_connector="planner-execution", data_lane="AB"[i])
    s += text(898, 981, "Same robot and policy · two user-conditioned executions", 12, MUTED, anchor="middle")
    for x, title, subtitle in [
        (28, "Task persona setup", "Hidden from policy · evaluation only"),
        (440, "Evaluate personalization", "Does the behavior fit this user?"),
        (852, "Robot-side evidence", "Inferred preference + execution"),
    ]:
        s += rect(x, 992, 320, 68, "#f7f9fc", LINE, 10)
        s += text(x+160, 1019, title, 15, weight=600, anchor="middle")
        s += text(x+160, 1042, subtitle, 12, MUTED, anchor="middle")
    s += arrow(356, 1026, 432, 1026, MUTED, "arrowGray", stroke_dasharray="4 4")
    s += arrow(844, 1026, 768, 1026, MUTED, "arrowGray", stroke_dasharray="4 4")
    s += text(28, 1093, "Conceptual mouse-placement example · Other objects stay fixed · Full Task 1 has additional goals.", 11, MUTED)
    return document(1200, 1108, s)


def mobile():
    s = text(28, 24, "PERSONALIZATION STARTS WITH THE USER", 12, BLUE, 700, letter_spacing=.5)
    s += text(28, 64, "Same Instruction,", 30, weight=600, letter_spacing=-.5)
    s += text(28, 100, "Different User Personas:", 30, weight=600, letter_spacing=-.5)
    s += text(28, 136, "Personalized Robot Actions.", 30, weight=600, letter_spacing=-.5)
    s += rect(28, 156, 544, 648, "#fff", LINE, 12, data_stage="user-inputs")
    for i, x in enumerate((44, 326)):
        color, pale = COLORS[i], PALES[i]
        s += rect(x, 172, 230, 486, pale, "none", 10)
        s += avatar(x+33, 208, color, pale, .75)
        s += text(x+66, 216, USER_NAMES[i], 23, color, 700)
        s += profile_components(x+16, 250, i, size=16, line_height=20, columns=25,
                                row_height=80, label_size=12, body_offset=22)
    s += '<g transform="translate(0 40)">'
    s += rect(44, 634, 512, 117, "#f7f9fc", "none", 9)
    s += text(300, 669, "IDENTICAL USER INSTRUCTION", 20, INK, 700, "middle")
    s += text(300, 715, USER_INSTRUCTION, 26, INK, 500, "middle", data_field="instruction")
    for i, cx in enumerate((159, 441)):
        s += arrow(cx, 772, cx, 804, COLORS[i], "arrow"+"AB"[i],
                   data_connector="profile-policy", data_lane="AB"[i])
    s += rect(28, 812, 544, 320, "#f7f9fc", LINE, 12, data_stage="policy")
    s += text(300, 850, "Select context, infer and plan", 27, weight=600, anchor="middle")
    s += text(300, 882, "Full profile + instruction + scene", 20, MUTED, anchor="middle")
    for i, x in enumerate((44, 326)):
        color, pale, letter = COLORS[i], PALES[i], "AB"[i]
        hand = ("left", "right")[i]
        s += rect(x, 904, 230, 204, pale, "none", 9)
        s += text(x+16, 932, "SELECT RELEVANT CUES", 13.5, color, 700)
        s += text(x+16, 960, "Computer work +", 17, INK)
        s += text(x+16, 983, "hand-use habits", 17, INK)
        s += arrow(x+115, 995, x+115, 1010, color, "arrow"+letter,
                   data_connector="context-preference", data_lane=letter)
        s += text(x+16, 1034, "INFER TASK PREFERENCE", 13, color, 700)
        s += text(x+16, 1065, f"Likely {hand}-side use", 18, MUTED)
        s += text(x+16, 1094, f"Plan: mouse → {hand}", 20, color, 600)
    for i, x in enumerate((28, 310)):
        color, pale, letter = COLORS[i], PALES[i], "AB"[i]
        cx, hub_y = x+131, 1516
        s += rect(x, 1180, 262, 676, pale, "none", 12)
        s += text(x+20, 1218, USER_NAMES[i], 25, color, 700)
        s += text(cx, 1253, "Before", 24, MUTED, 600, "middle")
        s += use_desk("desk-before", x+27, 1268, 4/3)
        s += execution_robot(cx, hub_y, color, letter, .35, 36)
        s += arrow(cx, 1448, cx, 1472, MUTED, "arrowGray",
                   data_connector="before-execution", data_lane=letter)
        s += arrow(cx, 1560, cx, 1580, color, "arrow"+letter,
                   data_connector="execution-after", data_lane=letter)
        label_x = cx + (-43 if i else 43)
        label_anchor = "end" if i else "start"
        s += text(label_x, 1494, "Plan & act", 18, INK, 600, label_anchor)
        s += text(cx, 1609, "After", 24, color, 600, "middle")
        s += use_desk("desk-after-"+str(i), x+27, 1626, 4/3)
        s += text(cx, 1166, "Top-down · user at bottom", 13, MUTED, 500, "middle")
    s += path("M300 1140 V1328 V1516", MUTED, 2, marker_mid="url(#arrowGray)", data_connector="planner-trunk")
    s += '<circle cx="300" cy="1132" r="3.5" fill="#607087"/>'
    s += '<circle cx="300" cy="1516" r="3.5" fill="#607087"/>'
    s += arrow(300, 1516, 203, 1516, BLUE, "arrowA", data_connector="planner-execution", data_lane="A")
    s += arrow(300, 1516, 397, 1516, TEAL, "arrowB", data_connector="planner-execution", data_lane="B")
    s += text(300, 1889, "Same Unitree G1 and policy for both users", 20, MUTED, anchor="middle")
    s += rect(28, 1918, 262, 90, "#f7f9fc", LINE, 10)
    s += rect(340, 1918, 232, 90, "#f7f9fc", LINE, 10)
    s += text(48, 1949, "Task persona setup", 21, weight=600)
    s += text(48, 1981, "Hidden from policy", 18, MUTED)
    s += arrow(298, 1963, 332, 1963, MUTED, "arrowGray", stroke_dasharray="4 4")
    s += text(456, 1950, "Evaluate", 27, weight=600, anchor="middle")
    s += text(456, 1982, "Preference + execution", 18, MUTED, anchor="middle")
    s += text(28, 2035, "Conceptual mouse example; full Task 1 has more goals.", 15, MUTED)
    s += '</g>'
    return document(600, 2088, s)


def main():
    assets = ROOT / "assets"
    (assets / "persona-concept.svg").write_text(desktop(), encoding="utf-8")
    (assets / "persona-concept-mobile.svg").write_text(mobile(), encoding="utf-8")
    print("Built desktop 1200×1108 and phone 600×2088 concept SVGs.")


if __name__ == "__main__":
    main()
