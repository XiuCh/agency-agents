"""
CRISPR-Cas9 靶向切割机制动画 (Manim Community Edition)

演示内容
    1. Cas9–sgRNA 复合物沿 DNA 扫描：无 PAM 不结合 → 有 PAM 但种子区错配则脱离 → PAM + 完全互补则锁定
    2. 近景（碱基水平）：PI 结构域读取 PAM (5'-NGG-3')
    3. 从 PAM 近端的种子区开始，sgRNA 与靶标链逐碱基配对，非靶标链被置换，形成 R-loop
    4. 氢键特写：A–U (2 个) / G–C (3 个) / 错配
    5. HNH 切靶标链、RuvC 切非靶标链，切点位于 PAM 上游 3 bp，产生平末端双链断裂 (DSB)

渲染
    pip install manim
    manim -pql crispr_cas9_manim.py CRISPRCas9      # 480p 预览
    manim -pqh crispr_cas9_manim.py CRISPRCas9      # 1080p 成片

中文字体
    默认使用 "Noto Sans CJK SC"。若系统没有该字体，可通过环境变量覆盖，例如
        macOS:   MANIM_CJK_FONT="PingFang SC"
        Windows: MANIM_CJK_FONT="Microsoft YaHei"
    本脚本不使用 LaTeX，无需安装 TeX。

说明
    - 序列、坐标与时序均为教学示意，非精确原子结构。
    - 以化脓链球菌 Cas9 (SpCas9) 为例：PAM = 5'-NGG-3'，位于非靶标链、紧邻原间隔序列 3' 端；
      sgRNA 5' 端 20 nt 间隔序列与靶标链互补；切点在 PAM 上游第 3 个与第 4 个碱基之间。
"""
import os

import numpy as np
from manim import *

CJK = os.environ.get("MANIM_CJK_FONT", "Noto Sans CJK SC")

# ---------- 配色 ----------
BG = "#0d1117"
C_NTS = "#5DA9FF"   # 非靶标链 (含 PAM)
C_TS = "#3DD6C0"    # 靶标链 (与 sgRNA 互补)
C_RNA = "#FF9F43"   # sgRNA
C_PAM = "#FFD93D"   # PAM
C_CAS = "#8E9AAF"   # Cas9
C_OK = "#6BCB77"
C_BAD = "#FF5C5C"
BASE_COL = {"A": "#6BCB77", "T": "#FF6B6B", "U": "#FF6B6B", "G": "#4D96FF", "C": "#FFD93D"}

# ---------- 序列 ----------
PROTO = "GACCTGAAGTCGATCCGTAC"          # 原间隔序列 (非靶标链 5'→3')，20 nt
PAM = "TGG"                              # 5'-NGG-3'，N = T
FLANK_L, FLANK_R = "AT", "CA"
NTS = FLANK_L + PROTO + PAM + FLANK_R    # 非靶标链 5'→3'
COMP = {"A": "T", "T": "A", "G": "C", "C": "G"}
TS = "".join(COMP[b] for b in NTS)       # 靶标链 (按 3'→5' 自左向右排列)
RNA = PROTO.replace("T", "U")            # sgRNA 间隔序列 5'→3'，与 NTS 同向、与 TS 反向平行配对
N = len(NTS)
J0 = len(FLANK_L)
assert len(PROTO) == 20 and PAM[1:] == "GG"


def col(p):
    """原间隔序列第 p 位 (1..20, 5'→3') 所在列。"""
    return J0 + p - 1


PAM_COLS = [col(20) + 1, col(20) + 2, col(20) + 3]

# ---------- 版面 ----------
SP = 0.5                                  # 碱基间距
Y_NTS, Y_TS = 0.6, -0.6                   # 双链
Y_RNA0, Y_RNA = -3.0, -1.8                # sgRNA 配对前 / 后
LIFT = 1.2                                # 非靶标链被置换时上抬的高度


def X(j):
    return (j - (N - 1) / 2) * SP


X_CUT = (X(col(17)) + X(col(18))) / 2     # 切点：第 17 与 18 位之间 (PAM 上游 3 bp)


# ---------- 小工具 ----------
def T(txt, size=24, color=WHITE, **kw):
    return Text(txt, font=CJK, font_size=size, color=color, **kw)


def letter(ch, color):
    t = Text(ch, font_size=26, weight=BOLD, color=color)
    t.set_stroke(BG, width=7, background=True)   # 用背景色描边，让骨架线在字母处"断开"
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
    """穿过一串字母中心的骨架线，随字母位置实时更新。"""
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
    """总览图中的 Cas9–sgRNA 复合物图标 (中心在原点，间隔序列朝下)。"""
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
    """碱基卡通：嘌呤 = 六元环 + 五元环，嘧啶 = 六元环。"""
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
    # ------------------------------------------------------------------ 字幕
    def say(self, text, size=26, wait=0.0):
        """屏幕底部字幕，随相机缩放/移动保持大小与位置。"""
        new = T(text, size)
        if new.width > 12.2:
            new.scale_to_fit_width(12.2)
        base_w = new.width

        def upd(m):
            s = self.camera.frame.width / config.frame_width
            m.scale_to_fit_width(base_w * s)
            m.move_to(self.camera.frame.get_bottom() + UP * (0.3 * s + m.height / 2))

        new.add_updater(upd)
        upd(new)
        anims = [FadeIn(new)]
        if self._cap is not None:
            anims.append(FadeOut(self._cap))
        self.play(*anims, run_time=0.5)
        self._cap = new
        if wait:
            self.wait(wait)

    def cam(self, width, center, rt=1.5):
        self.play(self.camera.frame.animate.scale_to_fit_width(width).move_to(center), run_time=rt)

    # ------------------------------------------------------------------ 主流程
    def construct(self):
        self.camera.background_color = BG
        self._cap = None
        self.intro()
        self.scan()
        self.build_closeup()
        self.recognize_pam()
        self.unwind_and_pair()
        self.hbond_detail()
        self.cleave()
        self.outro()

    # ------------------------------------------------------------------ 1. 片头
    def intro(self):
        title = T("CRISPR-Cas9 如何找到并切断靶 DNA", 44, WHITE, weight=BOLD)
        sub = T("Cas9 核酸酶  ·  sgRNA  ·  PAM  ·  靶序列", 26, GREY_B).next_to(title, DOWN, buff=0.4)
        self.play(Write(title), run_time=1.5)
        self.play(FadeIn(sub, shift=UP * 0.2))
        self.wait(1)
        self.play(title.animate.scale(0.55).to_edge(UP, buff=0.3), FadeOut(sub))

        legend = VGroup(*[
            VGroup(Square(0.16, stroke_width=0).set_fill(c, 1), T(name, 18, GREY_A)).arrange(RIGHT, buff=0.1)
            for name, c in [("Cas9", C_CAS), ("sgRNA", C_RNA), ("非靶标链", C_NTS), ("靶标链", C_TS),
                            ("PAM", C_PAM), ("原间隔序列", C_OK)]
        ]).arrange(RIGHT, buff=0.45).next_to(title, DOWN, buff=0.2)
        self.play(FadeIn(legend))
        self.title, self.legend = title, legend

    # ------------------------------------------------------------------ 2. 扫描 (总览)
    def scan(self):
        y1, y2 = -2.2, -2.7
        nts = Line([-6.8, y1, 0], [6.8, y1, 0], stroke_color=C_NTS, stroke_width=5)
        ts = Line([-6.8, y2, 0], [6.8, y2, 0], stroke_color=C_TS, stroke_width=5)
        rungs = VGroup(*[Line([x, y1, 0], [x, y2, 0], stroke_width=1.5, stroke_color=GREY_D)
                         for x in np.arange(-6.8, 6.85, 0.25)])
        dna_tag = T("基因组 DNA", 18, GREY_B).move_to([-6.0, -3.1, 0])
        self.play(FadeIn(VGroup(rungs, nts, ts, dna_tag)))

        # (PAM 左端 x, PAM 序列, PAM 合格?, 原间隔序列完全互补?)
        sites = [(-3.6, "TCA", False, True), (0.2, "CGG", True, False), (4.0, "TGG", True, True)]
        site_mobs = VGroup()
        pam_txt = []
        for xp, pam, pam_ok, proto_ok in sites:
            if proto_ok:
                segs = [Line([xp - 2.2, y1, 0], [xp - 0.05, y1, 0], stroke_color=C_OK, stroke_width=10)]
            else:   # 靠近 PAM 的种子区错配
                segs = [Line([xp - 2.2, y1, 0], [xp - 1.0, y1, 0], stroke_color=C_OK, stroke_width=10),
                        Line([xp - 1.0, y1, 0], [xp - 0.05, y1, 0], stroke_color=C_BAD, stroke_width=10)]
            pam_seg = Line([xp, y1, 0], [xp + 0.7, y1, 0], stroke_color=C_PAM if pam_ok else GREY_B, stroke_width=10)
            txt = T(pam, 20, C_PAM if pam_ok else GREY_B).move_to([xp + 0.35, y1 + 0.3, 0])
            pam_txt.append(txt)
            site_mobs.add(*segs, pam_seg, txt)
        self.play(FadeIn(site_mobs))

        cas9 = make_cas9().move_to([-6.2, -0.3, 0])
        self.play(FadeIn(cas9, shift=DOWN * 0.3))
        self.say("Cas9–sgRNA 复合物沿 DNA 扩散，逐段检测", wait=1.0)

        marks = VGroup()

        def go(xp):
            self.play(cas9.animate.move_to([xp - 0.5, -0.3, 0]), run_time=1.6)

        # 位点 1：序列互补，但没有 PAM
        xp = sites[0][0]
        go(xp)
        m = make_cross([xp + 0.35, -3.1, 0])
        marks.add(m)
        self.play(Create(m))
        self.say("位点 1：互补但无 PAM → Cas9 不解旋 DNA，立即脱离", wait=1.5)

        # 位点 2：有 PAM，但种子区错配
        xp = sites[1][0]
        go(xp)
        m = make_check([xp + 0.35, -3.1])
        marks.add(m)
        self.play(Create(m))
        self.say("位点 2：有 PAM (CGG) → 局部解旋，尝试与 sgRNA 配对", wait=1.0)
        m = make_cross([xp - 0.5, -3.1])
        marks.add(m)
        self.play(Create(m), Wiggle(cas9, scale_value=1.05, rotation_angle=0.03 * TAU))
        self.say("PAM 近端种子区错配 → R-loop 无法延伸 → 脱离", wait=1.5)

        # 位点 3：PAM + 完全互补
        xp = sites[2][0]
        go(xp)
        m1, m2 = make_check([xp + 0.35, -3.1]), make_check([xp - 1.1, -3.1])
        marks.add(m1, m2)
        self.play(Create(m1), Create(m2), Flash(pam_txt[2], color=C_PAM, flash_radius=0.5))
        self.say("位点 3：PAM (TGG) + 20 nt 完全互补 → 稳定结合，进入近景", wait=2.0)

        self.ov = VGroup(rungs, nts, ts, dna_tag, site_mobs, cas9, marks, self.legend)

    # ------------------------------------------------------------------ 3. 近景：构建双链与 sgRNA
    def build_closeup(self):
        f = self.camera.frame
        self.play(FadeOut(self.ov), FadeOut(self.title),
                  f.animate.scale_to_fit_width(17).move_to([0, -0.4, 0]), run_time=1.5)

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
            T("非靶标链\nNTS", 22, C_NTS).next_to(ends[0], LEFT, buff=0.1),
            T("靶标链\nTS", 22, C_TS).next_to(ends[2], LEFT, buff=0.1),
        )
        self.play(FadeIn(VGroup(*self.top, *self.bot, *self.run, self.bb_top, self.bb_bot, ends, tags)),
                  run_time=1.5)
        self.say("靶 DNA：非靶标链 (含 PAM) 与靶标链 (与 sgRNA 互补) 构成双链", wait=2.0)

        # Cas9 轮廓
        ghost = RoundedRectangle(width=12.8, height=7.0, corner_radius=0.9, stroke_color=C_CAS,
                                 stroke_width=3, stroke_opacity=0.7).set_fill(C_CAS, 0.1)
        ghost.move_to([0.4, -0.1, 0]).set_z_index(-1)
        ghost_lab = T("Cas9", 30, C_CAS).move_to([-5.4, 3.0, 0])

        # sgRNA：配对前位于 DNA 下方，5' 间隔序列已被 Cas9 预组织
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
        rna_tag = T("sgRNA\n间隔序列 20 nt", 20, C_RNA)
        rna_tag.add_updater(lambda m: m.next_to(rna5, LEFT, buff=0.1))

        self.play(FadeIn(ghost), FadeIn(ghost_lab))
        self.play(FadeIn(VGroup(*self.rna, self.bb_rna, scaffold, rna5, rna_tag)), run_time=1.5)
        self.say("sgRNA = 5' 端 20 nt 间隔序列 (决定靶向特异性) + 3' 端支架 (与 Cas9 结合)", wait=2.5)
        self.ghost = ghost

    # ------------------------------------------------------------------ 4. PAM 识别
    def recognize_pam(self):
        cols = PAM_COLS
        self.cam(8.5, [4.0, 0.4, 0])
        box = SurroundingRectangle(VGroup(*[self.top[j] for j in cols], *[self.bot[j] for j in cols]),
                                   color=C_PAM, buff=0.12, corner_radius=0.1)
        lab = T("PAM  5'-NGG-3'", 22, C_PAM).next_to(box, DOWN, buff=0.15).shift(RIGHT * 0.6)
        pi = badge("PI 结构域", [X(cols[1]), 1.7, 0], w=1.8)
        pi_lab = T("Arg1333 / Arg1335 识别 GG", 15, C_PAM).next_to(pi, UP, buff=0.1)
        arrows = VGroup(*[Arrow([X(j), 1.45, 0], [X(j), Y_NTS + 0.35, 0], buff=0.02, stroke_width=3,
                                max_tip_length_to_length_ratio=0.4, color=C_PAM) for j in cols[1:]])
        self.play(Create(box), FadeIn(lab))
        self.play(FadeIn(pi), FadeIn(pi_lab), Create(arrows))
        self.play(*[self.top[j].animate.set_color(C_PAM) for j in cols[1:]],
                  *[Indicate(self.top[j], color=C_PAM) for j in cols[1:]])
        self.say("第一步：PI 结构域读取 PAM (SpCas9：5'-NGG-3'，位于非靶标链)", wait=2.5)
        self.play(FadeOut(VGroup(pi, pi_lab, arrows)))
        self.pam_box, self.pam_lab = box, lab

    # ------------------------------------------------------------------ 5. 解旋与配对 (R-loop)
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
        # 种子区 (PAM 近端 10 nt)：自 PAM 向外依次解旋并与 sgRNA 配对
        self.cam(11.5, [3.25, -0.7, 0])
        self.say("第二步：自 PAM 起局部解旋，sgRNA 与靶标链先在 PAM 近端「种子区」配对", wait=1.0)
        self.pair(range(20, 10, -1), run_time=6)

        seed_cols = range(col(11), col(20) + 1)
        seed = SurroundingRectangle(
            VGroup(*[self.top[j] for j in seed_cols], *[self.rna[j - J0] for j in seed_cols]),
            color=C_OK, buff=0.15, corner_radius=0.1)
        seed_lab = T("种子区 seed (PAM 近端 ~10 nt)：必须严格互补", 18, C_OK).next_to(seed, UP, buff=0.1)
        self.play(Create(seed), FadeIn(seed_lab))
        self.say("种子区配对成功，才会继续向 PAM 远端推进", wait=2.0)

        # PAM 远端延伸
        self.cam(17.5, [0, -0.5, 0])
        self.say("配对向 PAM 远端延伸，非靶标链被置换，形成 R-loop", wait=0.5)
        self.pair(range(10, 0, -1), run_time=6)
        self.say("20 nt 全部配对 → R-loop 完成 → 触发核酸酶结构域构象变化", wait=2.5)
        self.play(FadeOut(VGroup(seed, seed_lab, self.pam_lab)))

    # ------------------------------------------------------------------ 6. 氢键特写
    def hbond_detail(self):
        D = np.array([0.0, -16.0, 0.0])
        # 面板 = (中心 x, 靶标链碱基, sgRNA 碱基, 是否配对)
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
                head = T(f"{r_ch}–{t_ch} 互补：{n} 个氢键", 20, C_OK)
                extra = VGroup()
            else:
                bonds = hbonds(D[0] + cx, y_a, y_b, 2, color=C_BAD)
                bonds.set_stroke(width=3)
                head = T(f"{r_ch} ··· {t_ch} 错配", 20, C_BAD)
                extra = make_cross(D + [cx, 0, 0]).scale(1.6)
            head.move_to(D + [cx, 2.3, 0])
            group.add(top, bot, bonds, head, extra)
        row_ts = T("靶标链 (DNA)", 20, C_TS).move_to(D + [-6.1, 1.0, 0])
        row_rna = T("sgRNA", 20, C_RNA).move_to(D + [-6.1, -1.0, 0])
        group.add(row_ts, row_rna)
        note = T("示意图：嘌呤 (A、G) 为双环，嘧啶 (C、U) 为单环", 16, GREY_B).move_to(D + [0, -2.4, 0])
        group.add(note)

        self.add(group)
        self.cam(14.2, D + [0, 0, 0], rt=2.0)
        self.say("特写：sgRNA 与靶标链按碱基互补配对 —— A–U 2 个氢键，G–C 3 个氢键", wait=3.0)
        self.say("错配破坏氢键与几何形状；种子区内一个错配即可使 R-loop 终止", wait=3.5)
        self.cam(17.5, [0, -0.5, 0], rt=2.0)
        self.remove(group)

    # ------------------------------------------------------------------ 7. 切割
    def cleave(self):
        self.cam(11.5, [1.8, 0.2, 0])
        self.say("第三步：HNH 切靶标链，RuvC 切非靶标链，切点均在 PAM 上游 3 bp", wait=0.5)
        xc = X_CUT
        hnh = badge("HNH", [xc, Y_NTS, 0], color=C_TS)
        ruvc = badge("RuvC", [xc - 1.2, 2.8, 0], color=C_NTS)
        a1 = Arrow(hnh.get_bottom(), [xc, Y_TS + 0.45, 0], buff=0.03, stroke_width=3, color=C_TS,
                   max_tip_length_to_length_ratio=0.5)
        a2 = Arrow(ruvc.get_bottom() + RIGHT * 0.3, [xc, Y_NTS + LIFT + 0.45, 0], buff=0.03, stroke_width=3,
                   color=C_NTS, max_tip_length_to_length_ratio=0.3)
        self.play(FadeIn(hnh), FadeIn(ruvc), Create(a1), Create(a2))

        brace = Brace(VGroup(*self.top[col(18):col(20) + 1]), UP, buff=0.15, color=C_PAM)
        brace_lab = T("PAM 上游 3 bp", 16, C_PAM).next_to(brace, UP, buff=0.05)
        self.play(GrowFromCenter(brace), FadeIn(brace_lab))
        self.wait(1)

        cut_n = Line([xc, Y_NTS + LIFT - 0.45, 0], [xc, Y_NTS + LIFT + 0.45, 0], stroke_color=C_BAD, stroke_width=6)
        cut_t = Line([xc, Y_TS - 0.45, 0], [xc, Y_TS + 0.45, 0], stroke_color=C_BAD, stroke_width=6)
        self.play(Create(cut_n), Create(cut_t))

        # 在切点处断开两条骨架线
        self.remove(self.bb_top, self.bb_bot)
        cut_at = col(18)
        parts = [backbone(self.top[:cut_at], C_NTS), backbone(self.top[cut_at:], C_NTS),
                 backbone(self.bot[:cut_at], C_TS), backbone(self.bot[cut_at:], C_TS)]
        self.add(*parts)
        self.play(Flash(cut_n, color=C_BAD, flash_radius=0.5), Flash(cut_t, color=C_BAD, flash_radius=0.5))

        # 被置换的非靶标链 (不与任何链配对) 的 PAM 远端部分松开
        loose = self.top[J0:cut_at]
        self.play(*[m.animate.shift(LEFT * 0.25 + UP * 0.2) for m in loose],
                  FadeOut(VGroup(hnh, ruvc, a1, a2, brace, brace_lab, cut_n, cut_t)), run_time=1.5)
        self.say("结果：切点处形成平末端双链断裂 (DSB)", wait=3.0)

    # ------------------------------------------------------------------ 8. 结尾
    def outro(self):
        self.cam(17, [0, -0.4, 0], rt=2.0)
        self.say("DSB 由细胞 NHEJ (易错，产生 indel → 基因敲除) 或 HDR (提供模板 → 精确编辑) 修复", wait=4.0)
        self.play(FadeOut(self._cap))
        self.wait(1)
