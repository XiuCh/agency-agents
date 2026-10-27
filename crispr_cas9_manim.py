"""
CRISPR-Cas9 target search, R-loop formation and cleavage (Manim Community Edition)
English narration (male neural voice) + English captions.

Storyline
    1. The Cas9-sgRNA complex scans DNA: no PAM -> no binding; PAM but seed mismatch -> release;
       PAM + full complementarity -> lock on
    2. Close-up: the PAM-interacting domain reads 5'-NGG-3'
    3. Starting at the PAM-proximal seed region, the sgRNA pairs with the target strand base by base,
       displacing the non-target strand (R-loop)
    4. Hydrogen-bond close-up: A-U (2), G-C (3), and a mismatch
    5. HNH cuts the target strand, RuvC cuts the non-target strand, 3 bp upstream of the PAM

Render
    pip install manim kokoro-onnx soundfile          # TTS is optional: without it the video is silent
    # Kokoro model files (one-off download):
    #   https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
    #   -> kokoro-v1.0.int8.onnx and voices-v1.0.bin
    export KOKORO_MODEL=/path/to/kokoro-v1.0.int8.onnx
    export KOKORO_VOICES=/path/to/voices-v1.0.bin
    manim -pql crispr_cas9_manim.py CRISPRCas9        # 480p preview
    manim -pqh crispr_cas9_manim.py CRISPRCas9        # 1080p60

Optional environment variables
    KOKORO_VOICE   voice name (default "am_michael"; other male voices: "am_adam", "bm_george")
    MANIM_FONT     font family for all text (default: system sans-serif)

Notes
    - Sequences, coordinates and timing are schematic, not atomic structures.
    - Based on S. pyogenes Cas9 (SpCas9): PAM = 5'-NGG-3' on the non-target strand, directly 3' of the
      protospacer; the 20-nt spacer pairs with the target strand; cleavage is 3 bp upstream of the PAM.
"""
import os

import numpy as np
from manim import *

FONT = os.environ.get("MANIM_FONT")
VOICE = os.environ.get("KOKORO_VOICE", "am_michael")

# ---------- colours ----------
BG = "#0d1117"
C_NTS = "#5DA9FF"   # non-target strand (carries the PAM)
C_TS = "#3DD6C0"    # target strand (complementary to the sgRNA)
C_RNA = "#FF9F43"   # sgRNA
C_PAM = "#FFD93D"   # PAM
C_CAS = "#8E9AAF"   # Cas9
C_OK = "#6BCB77"
C_BAD = "#FF5C5C"
BASE_COL = {"A": "#6BCB77", "T": "#FF6B6B", "U": "#FF6B6B", "G": "#4D96FF", "C": "#FFD93D"}

# ---------- sequences ----------
PROTO = "GACCTGAAGTCGATCCGTAC"          # protospacer (non-target strand 5'->3'), 20 nt
PAM = "TGG"                              # 5'-NGG-3', N = T
FLANK_L, FLANK_R = "AT", "CA"
NTS = FLANK_L + PROTO + PAM + FLANK_R    # non-target strand 5'->3'
COMP = {"A": "T", "T": "A", "G": "C", "C": "G"}
TS = "".join(COMP[b] for b in NTS)       # target strand (drawn 3'->5', left to right)
RNA = PROTO.replace("T", "U")            # sgRNA spacer 5'->3'; same sense as the NTS, pairs antiparallel with the TS
N = len(NTS)
J0 = len(FLANK_L)
assert len(PROTO) == 20 and PAM[1:] == "GG"


def col(p):
    """Column of protospacer position p (1..20, 5'->3')."""
    return J0 + p - 1


PAM_COLS = [col(20) + 1, col(20) + 2, col(20) + 3]

# ---------- layout ----------
SP = 0.5                                  # base spacing
Y_NTS, Y_TS = 0.6, -0.6                   # duplex rows
Y_RNA0, Y_RNA = -3.0, -1.8                # sgRNA row before / after pairing
LIFT = 1.2                                # how far the displaced non-target strand is lifted


def X(j):
    return (j - (N - 1) / 2) * SP


X_CUT = (X(col(17)) + X(col(18))) / 2     # cut site: between positions 17 and 18 (3 bp upstream of the PAM)


# ---------- helpers ----------
def T(txt, size=24, color=WHITE, **kw):
    if FONT:
        kw["font"] = FONT
    return Text(txt, font_size=size, color=color, **kw)


def wrap(text, width=60):
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return "\n".join(lines)


def letter(ch, color):
    t = Text(ch, font_size=26, weight=BOLD, color=color)
    t.set_stroke(BG, width=7, background=True)   # outline in the background colour so the backbone "breaks" behind each letter
    t.set_z_index(3)
    return t


def n_hbonds(a, b):
    return 3 if {a, b} == {"G", "C"} else 2


def hbonds(x, y_a, y_b, n, color=GREY_A):
    offs = {2: [-0.05, 0.05], 3: [-0.09, 0.0, 0.09]}[n]
    return VGroup(*[
        DashedLine([x + o, y_a, 0], [x + o, y_b, 0], dash_length=0.05,
                   stroke_width=1.8, stroke_color=color)
        for o in offs
    ])


def backbone(mobs, color, extra=None):
    """Backbone line through the centres of a row of letters; follows them as they move."""
    bb = VMobject(stroke_color=color, stroke_width=3, stroke_opacity=0.85)

    def upd(m):
        pts = [mm.get_center() for mm in mobs]
        if extra is not None:
            pts += extra(mobs)
        m.set_points_as_corners(pts)

    bb.add_updater(upd)
    upd(bb)
    return bb


def p3(pos):
    return np.array([*pos, 0.0])[:3]


def make_check(pos, color=C_OK):
    c = VMobject(stroke_color=color, stroke_width=6)
    c.set_points_as_corners([[-0.14, 0.0, 0], [-0.04, -0.12, 0], [0.18, 0.14, 0]])
    return c.move_to(p3(pos))


def make_cross(pos, color=C_BAD):
    return Cross(stroke_color=color, stroke_width=6).scale(0.14).move_to(p3(pos))


def badge(text, pos, color=C_CAS, w=1.3):
    box = RoundedRectangle(width=w, height=0.5, corner_radius=0.15, stroke_color=color, stroke_width=2.5)
    box.set_fill(color, 0.35)
    return VGroup(box, T(text, 20, WHITE)).move_to(pos)


def make_cas9():
    """Cas9-sgRNA icon for the overview (centred at the origin, spacer pointing down)."""
    body = Ellipse(width=2.5, height=1.7, stroke_color=C_CAS, stroke_width=3).set_fill(C_CAS, 0.3)
    lobe = Ellipse(width=1.3, height=1.0, stroke_width=0).set_fill(C_NTS, 0.25).move_to([0.55, 0.25, 0])
    guide = VMobject(stroke_color=C_RNA, stroke_width=5)
    guide.set_points_smoothly([[-1.0, 0.35, 0], [-0.55, 0.55, 0], [-0.1, 0.25, 0],
                               [-0.45, -0.1, 0], [-0.55, -0.5, 0], [-0.5, -0.95, 0]])
    dots = VGroup(*[Dot([-0.5 + 0.25 * i, -1.0, 0], radius=0.06, color=C_RNA) for i in range(5)])
    return VGroup(body, lobe, guide, dots,
                  T("Cas9", 28).move_to([0.55, 0.2, 0]),
                  T("sgRNA", 16, C_RNA).move_to([-1.55, -1.3, 0]))


def base_shape(ch, purine, flip=False, r=0.5):
    """Base cartoon: purine = six-membered + five-membered ring, pyrimidine = six-membered ring."""
    hexa = RegularPolygon(6, radius=r)
    parts = [hexa]
    if purine:
        a = 30 * DEGREES
        pent = RegularPolygon(5, start_angle=a, radius=0.8507 * r)
        pent.move_to(1.554 * r * np.array([np.cos(a), np.sin(a), 0]))
        parts.append(pent)
    body = VGroup(*parts).set_fill(BASE_COL[ch], 0.35).set_stroke(BASE_COL[ch], 3)
    if flip:
        body.flip(RIGHT)
    return VGroup(body, Text(ch, font_size=30, weight=BOLD).move_to(hexa.get_center()))


class CRISPRCas9(MovingCameraScene):
    # ------------------------------------------------------------------ voice-over
    def _load_tts(self):
        self._tts = None
        model = os.environ.get("KOKORO_MODEL")
        voices = os.environ.get("KOKORO_VOICES")
        if not (model and voices and os.path.exists(model) and os.path.exists(voices)):
            print("[voice-over] KOKORO_MODEL / KOKORO_VOICES not set: rendering silently")
            return
        try:
            from kokoro_onnx import Kokoro
            self._tts = Kokoro(model, voices)
        except Exception as e:  # noqa: BLE001
            print(f"[voice-over] TTS unavailable ({e}): rendering silently")

    def _voice(self, text):
        """Return (wav_path or None, duration in seconds); synthesised once and cached."""
        if self._tts is None:
            return None, len(text.split()) / 2.6
        import hashlib
        import soundfile as sf
        d = os.path.join(config.media_dir, "voiceover")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, hashlib.md5(f"{VOICE}|{text}".encode()).hexdigest() + ".wav")
        if not os.path.exists(path):
            samples, sr = self._tts.create(text, voice=VOICE, speed=0.95, lang="en-us")
            sf.write(path, samples, sr)
        info = sf.info(path)
        return path, info.frames / info.samplerate

    def _sync(self, gap=0.35):
        """Hold the animation until the current narration line has finished."""
        lag = self._audio_end + gap - self.renderer.time
        if lag > 0:
            self.wait(lag)

    # ------------------------------------------------------------------ captions
    def say(self, narration, caption=None, size=26, wait=0.0):
        """Speak `narration` and show it (or `caption`) at the bottom of the screen.

        Waits for the previous line to finish first, so audio never overlaps."""
        self._sync()
        new = T(wrap(caption or narration), size)
        if new.width > 12.4:
            new.scale_to_fit_width(12.4)
        base_w = new.width

        def upd(m):
            s = self.camera.frame.width / config.frame_width
            m.scale_to_fit_width(base_w * s)
            m.move_to(self.camera.frame.get_bottom() + UP * (0.3 * s + m.height / 2))

        new.add_updater(upd)
        upd(new)
        path, dur = self._voice(narration)
        if path:
            self.add_sound(path)
        self._audio_end = self.renderer.time + dur
        anims = [FadeIn(new)]
        if self._cap is not None:
            anims.append(FadeOut(self._cap))
        self.play(*anims, run_time=0.5)
        self._cap = new
        if wait:
            self.wait(wait)

    def cam(self, width, center, rt=1.5):
        self.play(self.camera.frame.animate.scale_to_fit_width(width).move_to(center), run_time=rt)

    # ------------------------------------------------------------------ main flow
    def construct(self):
        self.camera.background_color = BG
        self._cap = None
        self._audio_end = 0.0
        self._load_tts()
        self.intro()
        self.scan()
        self.build_closeup()
        self.recognize_pam()
        self.unwind_and_pair()
        self.hbond_detail()
        self.cleave()
        self.outro()

    # ------------------------------------------------------------------ 1. title
    def intro(self):
        title = T("How CRISPR-Cas9 Finds and Cuts Its Target DNA", 42, WHITE, weight=BOLD)
        sub = T("Cas9 nuclease  ·  sgRNA  ·  PAM  ·  target sequence", 26, GREY_B).next_to(title, DOWN, buff=0.4)
        title.scale_to_fit_width(12.5)
        self.play(Write(title), run_time=1.5)
        self.play(FadeIn(sub, shift=UP * 0.2))
        self.say("How does CRISPR-Cas9 find one exact sequence among billions of base pairs, and then cut it?")
        self.wait(1)
        self.play(title.animate.scale(0.55).to_edge(UP, buff=0.3), FadeOut(sub))

        legend = VGroup(*[
            VGroup(Square(0.16, stroke_width=0).set_fill(c, 1), T(name, 18, GREY_A)).arrange(RIGHT, buff=0.1)
            for name, c in [("Cas9", C_CAS), ("sgRNA", C_RNA), ("Non-target strand", C_NTS),
                            ("Target strand", C_TS), ("PAM", C_PAM), ("Protospacer", C_OK)]
        ]).arrange(RIGHT, buff=0.4).next_to(title, DOWN, buff=0.2)
        self.play(FadeIn(legend))
        self.say("The key players are the Cas9 nuclease, a guide RNA, and a short motif called the PAM.", wait=1.0)
        self.title, self.legend = title, legend

    # ------------------------------------------------------------------ 2. scanning (overview)
    def scan(self):
        y1, y2 = -1.9, -2.4
        nts = Line([-6.8, y1, 0], [6.8, y1, 0], stroke_color=C_NTS, stroke_width=5)
        ts = Line([-6.8, y2, 0], [6.8, y2, 0], stroke_color=C_TS, stroke_width=5)
        rungs = VGroup(*[Line([x, y1, 0], [x, y2, 0], stroke_width=1.5, stroke_color=GREY_D)
                         for x in np.arange(-6.8, 6.85, 0.25)])
        dna_tag = T("Genomic DNA", 18, GREY_B).move_to([-6.0, -2.8, 0])
        self.play(FadeIn(VGroup(rungs, nts, ts, dna_tag)))

        # (PAM left edge x, PAM sequence, valid PAM?, protospacer fully complementary?)
        sites = [(-3.6, "TCA", False, True), (0.2, "CGG", True, False), (4.0, "TGG", True, True)]
        site_mobs = VGroup()
        pam_txt = []
        for xp, pam, pam_ok, proto_ok in sites:
            if proto_ok:
                segs = [Line([xp - 2.2, y1, 0], [xp - 0.05, y1, 0], stroke_color=C_OK, stroke_width=10)]
            else:   # mismatch in the PAM-proximal seed region
                segs = [Line([xp - 2.2, y1, 0], [xp - 1.0, y1, 0], stroke_color=C_OK, stroke_width=10),
                        Line([xp - 1.0, y1, 0], [xp - 0.05, y1, 0], stroke_color=C_BAD, stroke_width=10)]
            pam_seg = Line([xp, y1, 0], [xp + 0.7, y1, 0], stroke_color=C_PAM if pam_ok else GREY_B, stroke_width=10)
            txt = T(pam, 20, C_PAM if pam_ok else GREY_B).move_to([xp + 0.35, y1 + 0.3, 0])
            pam_txt.append(txt)
            site_mobs.add(*segs, pam_seg, txt)
        self.play(FadeIn(site_mobs))

        cas9 = make_cas9().move_to([-6.2, 0.1, 0])
        self.play(FadeIn(cas9, shift=DOWN * 0.3))
        self.say("The Cas9-sgRNA complex diffuses along the genome, testing one site at a time.", wait=1.0)

        marks = VGroup()

        def go(xp):
            self.play(cas9.animate.move_to([xp - 0.5, 0.1, 0]), run_time=1.6)

        # site 1: complementary, but no PAM
        xp = sites[0][0]
        go(xp)
        m = make_cross([xp + 0.35, -2.8, 0])
        marks.add(m)
        self.play(Create(m))
        self.say("Site one matches the guide but has no PAM, so Cas9 never unwinds the DNA and moves on.", wait=1.0)

        # site 2: PAM present, seed mismatch
        xp = sites[1][0]
        go(xp)
        m = make_check([xp + 0.35, -2.8])
        marks.add(m)
        self.play(Create(m))
        self.say("Site two has a PAM, so Cas9 starts to unwind the DNA and tries to pair with the guide.", wait=1.0)
        m = make_cross([xp - 0.5, -2.8])
        marks.add(m)
        self.play(Create(m), Wiggle(cas9, scale_value=1.05, rotation_angle=0.03 * TAU))
        self.say("But the seed region is mismatched, so pairing stalls and the complex lets go.", wait=1.0)

        # site 3: PAM + full complementarity
        xp = sites[2][0]
        go(xp)
        m1, m2 = make_check([xp + 0.35, -2.8]), make_check([xp - 1.1, -2.8])
        marks.add(m1, m2)
        self.play(Create(m1), Create(m2), Flash(pam_txt[2], color=C_PAM, flash_radius=0.5))
        self.say("Site three has a PAM and a perfectly complementary target, so the complex locks on. "
                 "Let's zoom in.", wait=1.0)

        self.ov = VGroup(rungs, nts, ts, dna_tag, site_mobs, cas9, marks, self.legend)

    # ------------------------------------------------------------------ 3. close-up: duplex + sgRNA
    def build_closeup(self):
        self._sync()
        f = self.camera.frame
        self.play(FadeOut(self.ov), FadeOut(self.title),
                  f.animate.scale_to_fit_width(17.5).move_to([0, -0.5, 0]), run_time=1.5)

        self.top = [letter(c, C_NTS).move_to([X(j), Y_NTS, 0]) for j, c in enumerate(NTS)]
        self.bot = [letter(c, C_TS).move_to([X(j), Y_TS, 0]) for j, c in enumerate(TS)]
        self.run = [hbonds(X(j), Y_NTS - 0.27, Y_TS + 0.27, n_hbonds(NTS[j], TS[j])) for j in range(N)]
        self.bb_top = backbone(self.top, C_NTS)
        self.bb_bot = backbone(self.bot, C_TS)

        def end(txt, x, y, color):
            return T(txt, 22, color).move_to([x, y, 0])

        ends = VGroup(
            end("5'", X(0) - 0.45, Y_NTS, C_NTS), end("3'", X(N - 1) + 0.45, Y_NTS, C_NTS),
            end("3'", X(0) - 0.45, Y_TS, C_TS), end("5'", X(N - 1) + 0.45, Y_TS, C_TS),
        )
        tags = VGroup(
            T("Non-target\nstrand", 16, C_NTS).next_to(ends[0], LEFT, buff=0.1),
            T("Target\nstrand", 16, C_TS).next_to(ends[2], LEFT, buff=0.1),
        )
        self.play(FadeIn(VGroup(*self.top, *self.bot, *self.run, self.bb_top, self.bb_bot, ends, tags)),
                  run_time=1.5)
        self.say("Here is the target DNA. The non-target strand carries the PAM; "
                 "the target strand pairs with the guide RNA.", wait=1.0)

        # Cas9 outline
        ghost = RoundedRectangle(width=12.8, height=7.0, corner_radius=0.9, stroke_color=C_CAS,
                                 stroke_width=3, stroke_opacity=0.7).set_fill(C_CAS, 0.1)
        ghost.move_to([0.4, -0.1, 0]).set_z_index(-1)
        ghost_lab = T("Cas9", 30, C_CAS).move_to([-5.4, 3.0, 0])

        # sgRNA: below the DNA before pairing; the 5' spacer is pre-organised by Cas9
        self.rna = [letter(c, C_RNA).move_to([X(col(p)), Y_RNA0, 0]) for p, c in enumerate(RNA, 1)]
        self.hb = [hbonds(X(col(p)), Y_TS - 0.27, Y_RNA + 0.27, n_hbonds(RNA[p - 1].replace("U", "T"),
                                                                       TS[col(p)]))
                   for p in range(1, 21)]
        scaffold_offs = [(0, 0), (0.5, -0.35), (1.0, -0.2), (1.5, -0.45), (1.9, -0.2)]
        self.bb_rna = backbone(self.rna, C_RNA)
        scaffold = VMobject(stroke_color=C_RNA, stroke_width=3, stroke_opacity=0.85)

        def upd_scaffold(m):
            c = self.rna[-1].get_center()
            m.set_points_smoothly([c + np.array([dx, dy, 0]) for dx, dy in scaffold_offs])

        scaffold.add_updater(upd_scaffold)
        upd_scaffold(scaffold)
        rna5 = T("5'", 22, C_RNA)
        rna5.add_updater(lambda m: m.next_to(self.rna[0], LEFT, buff=0.15))
        rna_tag = T("sgRNA\n20-nt spacer", 16, C_RNA)
        rna_tag.add_updater(lambda m: m.next_to(rna5, LEFT, buff=0.1))

        self.play(FadeIn(ghost), FadeIn(ghost_lab))
        self.play(FadeIn(VGroup(*self.rna, self.bb_rna, scaffold, rna5, rna_tag)), run_time=1.5)
        self.say("The guide has a twenty-nucleotide spacer that sets specificity, "
                 "plus a scaffold that binds Cas9.", wait=1.0)
        self.ghost = ghost

    # ------------------------------------------------------------------ 4. PAM recognition
    def recognize_pam(self):
        cols = PAM_COLS
        self._sync()
        self.cam(9, [4.0, 0.0, 0])
        box = SurroundingRectangle(VGroup(*[self.top[j] for j in cols], *[self.bot[j] for j in cols]),
                                   color=C_PAM, buff=0.12, corner_radius=0.1)
        lab = T("PAM  5'-NGG-3'", 22, C_PAM).next_to(box, DOWN, buff=0.15).shift(RIGHT * 0.25)
        pi = badge("PI domain", [X(cols[1]), 1.7, 0], w=1.8)
        pi_lab = T("Arg1333 / Arg1335 read the GG", 15, C_PAM).next_to(pi, UP, buff=0.1)
        arrows = VGroup(*[Arrow([X(j), 1.45, 0], [X(j), Y_NTS + 0.35, 0], buff=0.02, stroke_width=3,
                                max_tip_length_to_length_ratio=0.4, color=C_PAM) for j in cols[1:]])
        self.say("First, the PAM-interacting domain reads the PAM, N G G. "
                 "Arginines 1333 and 1335 contact the two guanines.",
                 caption="First, the PAM-interacting domain reads the PAM, 5'-NGG-3'. "
                         "Arg1333 and Arg1335 contact the two guanines.")
        self.play(Create(box), FadeIn(lab))
        self.play(FadeIn(pi), FadeIn(pi_lab), Create(arrows))
        self.play(*[self.top[j].animate.set_color(C_PAM) for j in cols[1:]],
                  *[Indicate(self.top[j], color=C_PAM) for j in cols[1:]])
        self.wait(1.5)
        self.play(FadeOut(VGroup(pi, pi_lab, arrows)))
        self.pam_box, self.pam_lab = box, lab

    # ------------------------------------------------------------------ 5. unwinding and pairing (R-loop)
    def pair(self, ps, run_time):
        anims = []
        for p in ps:
            j = col(p)
            anims.append(Succession(
                AnimationGroup(self.top[j].animate.shift(UP * LIFT),
                               FadeOut(self.run[j]),
                               self.rna[p - 1].animate.shift(UP * (Y_RNA - Y_RNA0))),
                FadeIn(self.hb[p - 1]),
            ))
        self.play(LaggedStart(*anims, lag_ratio=0.3), run_time=run_time)

    def unwind_and_pair(self):
        # seed region (PAM-proximal 10 nt): unwinds and pairs outward from the PAM
        self._sync()
        self.cam(12, [3.25, -0.85, 0])
        self.say("Next, the DNA unwinds beside the PAM, and the guide pairs with the target strand, "
                 "starting in the seed region.", wait=1.0)
        self.pair(range(20, 10, -1), run_time=6)

        seed_cols = range(col(11), col(20) + 1)
        seed = SurroundingRectangle(
            VGroup(*[self.top[j] for j in seed_cols], *[self.rna[j - J0] for j in seed_cols]),
            color=C_OK, buff=0.15, corner_radius=0.1)
        seed_lab = T("Seed region (PAM-proximal ~10 nt): must match exactly", 18, C_OK).next_to(seed, UP, buff=0.1)
        self.play(Create(seed), FadeIn(seed_lab))
        self.say("Only if the seed pairs perfectly does the complex continue.", wait=1.0)

        # extension toward the PAM-distal end
        self._sync()
        self.cam(17.5, [0, -0.5, 0])
        self.say("Pairing zips toward the far end, displacing the non-target strand and forming an R-loop.",
                 wait=0.5)
        self.pair(range(10, 0, -1), run_time=6)
        self.say("With all twenty nucleotides paired, the R-loop is complete and Cas9 activates "
                 "its two nuclease domains.", wait=1.0)
        self._sync()
        self.play(FadeOut(VGroup(seed, seed_lab, self.pam_lab)))

    # ------------------------------------------------------------------ 6. hydrogen-bond close-up
    def hbond_detail(self):
        D = np.array([0.0, -16.0, 0.0])
        # panel = (centre x, target-strand base, sgRNA base, paired?)
        panels = [(-3.3, "A", "U", True), (1.0, "G", "C", True), (5.3, "A", "C", False)]
        group = VGroup()
        for cx, t_ch, r_ch, ok in panels:
            top = base_shape(t_ch, t_ch in "AG").move_to(D + [cx, 1.0, 0])
            bot = base_shape(r_ch, r_ch in "AG", flip=True).move_to(D + [cx, -1.0, 0])
            y_a, y_b = D[1] + 0.567, D[1] - 0.567
            if ok:
                n = n_hbonds(t_ch, r_ch.replace("U", "T"))
                bonds = hbonds(D[0] + cx, y_a, y_b, n, color=C_OK)
                bonds.set_stroke(width=3)
                head = T(f"{r_ch}–{t_ch} pair: {n} H-bonds", 20, C_OK)
                extra = VGroup()
            else:
                bonds = hbonds(D[0] + cx, y_a, y_b, 2, color=C_BAD)
                bonds.set_stroke(width=3)
                head = T(f"{r_ch} ··· {t_ch} mismatch", 20, C_BAD)
                extra = make_cross(D + [cx, 0, 0]).scale(1.6)
            head.move_to(D + [cx, 2.3, 0])
            group.add(top, bot, bonds, head, extra)
        row_ts = T("Target strand\n(DNA)", 20, C_TS).move_to(D + [-6.1, 1.0, 0])
        row_rna = T("sgRNA", 20, C_RNA).move_to(D + [-6.1, -1.0, 0])
        group.add(row_ts, row_rna)
        note = T("Schematic: purines (A, G) have two rings; pyrimidines (C, U) have one", 16, GREY_B)
        note.move_to(D + [0, -2.4, 0])
        group.add(note)

        self.add(group)
        self._sync()
        self.cam(14.2, D + [0, 0, 0], rt=2.0)
        self.say("Up close: A pairs with U through two hydrogen bonds, and G pairs with C through three.", wait=1.0)
        self.say("A mismatch breaks the hydrogen bonding and distorts the geometry. "
                 "One seed mismatch can halt the R-loop.", wait=1.0)
        self._sync()
        self.cam(17.5, [0, -0.5, 0], rt=2.0)
        self.remove(group)

    # ------------------------------------------------------------------ 7. cleavage
    def cleave(self):
        self.cam(12.5, [1.8, 0.2, 0])
        self.say("Now HNH cuts the target strand and RuvC cuts the non-target strand, "
                 "both three base pairs upstream of the PAM.", wait=0.5)
        xc = X_CUT
        hnh = badge("HNH", [xc, Y_NTS, 0], color=C_TS)
        ruvc = badge("RuvC", [xc - 1.2, 2.8, 0], color=C_NTS)
        a1 = Arrow(hnh.get_bottom(), [xc, Y_TS + 0.45, 0], buff=0.03, stroke_width=3, color=C_TS,
                   max_tip_length_to_length_ratio=0.5)
        a2 = Arrow(ruvc.get_bottom() + RIGHT * 0.3, [xc, Y_NTS + LIFT + 0.45, 0], buff=0.03, stroke_width=3,
                   color=C_NTS, max_tip_length_to_length_ratio=0.3)
        self.play(FadeIn(hnh), FadeIn(ruvc), Create(a1), Create(a2))

        brace = Brace(VGroup(*self.top[col(18):col(20) + 1]), UP, buff=0.15, color=C_PAM)
        brace_lab = T("3 bp upstream of PAM", 16, C_PAM).next_to(brace, UP, buff=0.05)
        self.play(GrowFromCenter(brace), FadeIn(brace_lab))
        self._sync()
        self.wait(0.5)

        cut_n = Line([xc, Y_NTS + LIFT - 0.45, 0], [xc, Y_NTS + LIFT + 0.45, 0], stroke_color=C_BAD, stroke_width=6)
        cut_t = Line([xc, Y_TS - 0.45, 0], [xc, Y_TS + 0.45, 0], stroke_color=C_BAD, stroke_width=6)
        self.play(Create(cut_n), Create(cut_t))

        # break both backbones at the cut site
        self.remove(self.bb_top, self.bb_bot)
        cut_at = col(18)
        parts = [backbone(self.top[:cut_at], C_NTS), backbone(self.top[cut_at:], C_NTS),
                 backbone(self.bot[:cut_at], C_TS), backbone(self.bot[cut_at:], C_TS)]
        self.add(*parts)
        self.play(Flash(cut_n, color=C_BAD, flash_radius=0.5), Flash(cut_t, color=C_BAD, flash_radius=0.5))

        # the displaced non-target strand (paired with nothing) loosens on the PAM-distal side
        loose = self.top[J0:cut_at]
        self.play(*[m.animate.shift(LEFT * 0.25 + UP * 0.2) for m in loose],
                  FadeOut(VGroup(hnh, ruvc, a1, a2, brace, brace_lab, cut_n, cut_t)), run_time=1.5)
        self.say("The result is a blunt double-strand break.", wait=1.0)

    # ------------------------------------------------------------------ 8. outro
    def outro(self):
        self._sync()
        self.cam(17, [0, -0.4, 0], rt=2.0)
        self.say("The cell repairs the break by error-prone end joining, which can knock out the gene, "
                 "or by template-guided repair for precise edits.",
                 caption="The cell repairs the break by NHEJ (error-prone, can knock out the gene) "
                         "or HDR (template-guided, precise editing).")
        self._sync(gap=1.0)
        self.play(FadeOut(self._cap))
        self.wait(1)
