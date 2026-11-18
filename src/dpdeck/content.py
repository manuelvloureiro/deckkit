"""The deck: every slide, in order, with its text.

Text uses the inline markup of `richtext.py`: `*x*` for a variable, `**x**` for strong, `^{x}` and
`_{x}` for raised and lowered pieces of an equation.
"""

from __future__ import annotations

from dpdeck import plots
from dpdeck.model import (
    Card,
    CardsSlide,
    Cover,
    DataTable,
    Deck,
    Def,
    DiagramSlide,
    Eq,
    KeyLine,
    Node,
    Note,
    PlotSlide,
    Say,
    Section,
    Slide,
    Stat,
    Statement,
    TableSlide,
    TablesSlide,
    Term,
    Tight,
)

GAUSSIAN_DELTA = "*δ* = Φ(Δ/2*σ* − *εσ*/Δ) − *e*^{*ε*} · Φ(−Δ/2*σ* − *εσ*/Δ)"
SURVEY_HEADER = ("Person", "Smokes?")
SURVEY_ROWS = (
    ("Bob", "no"),
    ("Carol", "yes"),
    ("Dan", "no"),
    ("Eve", "yes"),
    ("15 more people", "5 yes, 10 no"),
)


def _why() -> list[Slide]:
    return [
        Cover(
            "cover",
            "A 20-minute introduction",
            "Differential privacy and privacy accounting",
            "From ε to zero-concentrated, in pictures",
            plots.cover_art(),
        ),
        CardsSlide(
            "objectives",
            "Objectives",
            "What you will be able to do in 20 minutes",
            (
                Card(
                    "State the promise",
                    "Say what differential privacy guarantees to one person, and read its definition "
                    "and its parameter ε.",
                    step="1",
                ),
                Card(
                    "Read the picture",
                    "See how noise sized to the sensitivity gives ε, and what δ adds when the noise is Gaussian.",
                    step="2",
                ),
                Card(
                    "Count the cost",
                    "Explain why every release spends privacy, and how ε and (ε, δ) add up over several releases.",
                    step="3",
                ),
                Card(
                    "Account more tightly",
                    "Say what concentrated and zero-concentrated differential privacy track, and why "
                    "they cost less over many releases.",
                    step="4",
                ),
            ),
            "No background assumed. Each definition is first a picture of two curves, then one line of math.",
        ),
        TablesSlide(
            "leak",
            "Why privacy needs a definition",
            "One person moves the count",
            (
                DataTable(
                    KeyLine("d", "*D*: the survey, 19 people"),
                    SURVEY_HEADER,
                    (*SURVEY_ROWS, (" ", " ")),
                    "7",
                    "published: the number of yes",
                ),
                DataTable(
                    KeyLine("dp", "*D′*: the same survey plus Alice"),
                    SURVEY_HEADER,
                    (*SURVEY_ROWS, ("**Alice**", "**yes**")),
                    "8",
                    "published: the number of yes",
                    highlight=5,
                ),
            ),
            (
                Say("A survey asks people whether they smoke, and publishes one number: how many said yes."),
                Say("Add one person, Alice, and the published number moves from 7 to 8. Nothing else differs."),
                Say(
                    "So the exact count carries her record. Anyone who knows the other 19 answers reads "
                    "it off, and removing the names changes nothing."
                ),
                Say("**A safe release must look almost the same with and without her.**"),
            ),
        ),
        DiagramSlide(
            "promise",
            "Why privacy needs a definition",
            "The promise",
            "With or without any one person, the output looks almost the same.",
            (
                Node(0, 0, 460, 140, "the data", title="Dataset *D*", key="d"),
                Node(0, 180, 460, 140, "the same data plus one person", title="Neighbour *D′*", key="dp"),
                Node(640, 75, 400, 170, "computes the answer, then adds random noise", title="Mechanism *M*"),
                Node(
                    1220,
                    10,
                    444,
                    300,
                    "Two sets of possible outputs that are hard to tell apart",
                    scene=plots.promise_outputs(),
                ),
            ),
            ((460, 70, 640, 135), (460, 250, 640, 185), (1040, 160, 1220, 160)),
            (
                Term("Pr[*M*(*D*) ∈ *S*]", "chance the output lands in *S*, on *D*", key="d"),
                Term("≤ *e*^{*ε*} ·", "“almost the same”"),
                Term("Pr[*M*(*D′*) ∈ *S*]", "the same chance, on *D′*", key="dp"),
            ),
            "ε-differential privacy: for every pair of neighbours *D*, *D′* and every set of outputs *S*. "
            "The smaller ε, the closer the two.",
        ),
    ]


def _basics() -> list[Slide]:
    basics = "The basics"
    return [
        PlotSlide(
            "sensitivity",
            basics,
            "Sensitivity and noise",
            plots.sensitivity(),
            (
                Def(
                    "Sensitivity",
                    (
                        Eq("Δ = max |*f*(*D*) − *f*(*D′*)|"),
                        Note("over all pairs of neighbours *D*, *D′*"),
                    ),
                ),
                Say("One person moves the true count *f* by at most Δ = 1: here from 7 to 8."),
                Say(
                    "Publish the count plus random noise. Each world becomes a curve of possible "
                    "published counts, and the two curves sit Δ apart."
                ),
            ),
        ),
        PlotSlide(
            "pure-dp",
            basics,
            "ε-differential privacy",
            plots.pure_dp(),
            (
                Def(
                    "ε-differential privacy, on the curves",
                    (
                        Eq("Pr[*M*(*D*) = *y*] ≤ *e*^{*ε*} · Pr[*M*(*D′*) = *y*]", "s"),
                        Note("at every output *y*, and with *D* and *D′* swapped. Here ε = 1: a factor of 2.7."),
                    ),
                ),
                Def(
                    "Laplace mechanism",
                    (
                        Eq("*M*(*D*) = *f*(*D*) + Lap(Δ/*ε*)"),
                        Eq("Lap(*b*) has density  (1/2*b*) · *e*^{−|*z*|/*b*}", "s"),
                    ),
                ),
                Say(
                    "No published count is more than 2.7 times as likely without Alice as with her. "
                    "Scale Δ/ε is the least noise that does this."
                ),
            ),
        ),
        CardsSlide(
            "calibration",
            basics,
            "The least noise that covers",
            (
                Card(
                    "Too little noise",
                    "Scale Δ/(2ε). The curves are too narrow to cover: this release is not ε-private.",
                    scene=plots.calibration_panel(
                        0.5, "Narrow curves. Left of 7 the blue curve rises above the dashed curve", True
                    ),
                ),
                Card(
                    "Just enough: scale Δ/ε",
                    "Blue touches the stretched curve and never passes it. This is the noise the "
                    "Laplace mechanism adds.",
                    scene=plots.calibration_panel(
                        1.0,
                        "Wider curves. Left of 7 the blue curve lies exactly on the dashed curve and never above it",
                        False,
                    ),
                ),
                Card(
                    "More than needed",
                    "Scale 2Δ/ε. Covered with room to spare, but the published count is less accurate for nothing.",
                    scene=plots.calibration_panel(
                        2.0, "Still wider curves. The dashed curve lies well above the blue curve everywhere", False
                    ),
                ),
            ),
            "The noise is chosen as the smallest that lets the stretched curve cover.",
            keys=(
                KeyLine("d", "published count on *D*"),
                KeyLine("dp", "published count on *D′*"),
                KeyLine("dash", "orange curve × 2.7, for ε = 1"),
            ),
            compact=True,
        ),
        PlotSlide(
            "log-scale",
            basics,
            "The same picture on a log scale",
            plots.log_scale(),
            (
                Say(
                    "On a log scale, multiplying by 2.7 becomes lifting by ε = 1, and the Laplace "
                    "curves become straight lines."
                ),
                Def(
                    "Privacy loss of an output *y*",
                    (Eq("*L*(*y*) = ln Pr[*M*(*D*) = *y*] − ln Pr[*M*(*D′*) = *y*]", "s"),),
                ),
                Say(
                    "The loss is the gap between blue and orange. It never exceeds ε, so the lifted "
                    "curve always covers the blue one."
                ),
            ),
        ),
        PlotSlide(
            "gaussian",
            basics,
            "Gaussian noise",
            plots.gaussian(),
            (
                Def("Gaussian mechanism", (Eq("*M*(*D*) = *f*(*D*) + *N*(0, *σ*²)"), Note("in this picture σ = Δ"))),
                Say("Gaussian noise is the workhorse of private machine learning. The curves are bells now."),
                Say(
                    "Multiply the orange curve by 2.7 as before. This time it does not cover the blue "
                    "curve: blue sticks out on the left."
                ),
            ),
        ),
        PlotSlide(
            "gaussian-log",
            basics,
            "Why no ε is enough",
            plots.gaussian_log(),
            (
                Say(
                    "On a log scale the bells are parabolas. The dashed curve sits ε above the orange "
                    "one at every point, measured straight up. Steep slopes only make the two look closer."
                ),
                Say(
                    "The gap between blue and orange keeps growing, so however far orange is lifted, "
                    "blue comes out above it somewhere. No ε is enough on its own."
                ),
                Say(
                    "The published counts where blue escapes are unlikely, though. The next definition "
                    "measures how unlikely."
                ),
            ),
        ),
        PlotSlide(
            "approx-dp",
            basics,
            "(ε, δ)-differential privacy",
            plots.approx_dp(),
            (
                Def(
                    "(ε, δ)-differential privacy",
                    (
                        Eq("Pr[*M*(*D*) ∈ *S*] ≤ *e*^{*ε*} · Pr[*M*(*D′*) ∈ *S*] + *δ*", "s"),
                        Note("for all neighbours *D*, *D′* and every set of outputs *S*"),
                    ),
                ),
                Say(
                    "δ is the probability that the stretched curve fails to cover: the area of blue "
                    f"above it. Here (ε, δ) = (1, {plots.DELTA_1:.2f})."
                ),
                Note(
                    "σ is set the same way as before: the least noise that leaves at most δ uncovered. "
                    "In practice δ is tiny, far below 1/*n* for *n* people. Here it is large so that "
                    "the area shows."
                ),
            ),
        ),
    ]


def _loss() -> list[Slide]:
    eyebrow = "The privacy loss"
    return [
        PlotSlide(
            "loss-distribution",
            eyebrow,
            "The privacy loss distribution",
            plots.loss_distribution(),
            (
                Say("Draw a published count, read off its gap, repeat. The gaps form the privacy loss distribution."),
                Def(
                    "For Gaussian noise, a bell again",
                    (
                        Tight((Eq("*L* ~ *N*(*μ*, 2*μ*)"), Eq("*μ* = Δ² / (2*σ*²)"))),
                        Note("in the picture σ = Δ, so μ = 0.5"),
                    ),
                ),
                Say(
                    "A wall at ε splits the bell. Beyond it lie the counts where blue stuck out, and δ "
                    "is the uncovered share of that tail."
                ),
            ),
        ),
        PlotSlide(
            "many-pairs",
            eyebrow,
            "One mechanism, many (ε, δ) pairs",
            plots.many_pairs(),
            (
                Say("Move the wall and the uncovered part changes: every ε has its own δ."),
                Def(
                    "The δ that goes with each ε",
                    (
                        Eq("*δ*(*ε*) = E[max(0, 1 − *e*^{*ε* − *L*})]"),
                        Note(
                            "the uncovered share of the bell beyond the wall at ε. For Gaussian noise it works out to"
                        ),
                        Eq(GAUSSIAN_DELTA, "s"),
                        Note("Φ: the area under a standard bell left of a point"),
                    ),
                ),
                Say(
                    "One mechanism satisfies a whole curve of (ε, δ) pairs. A single pair is a lossy "
                    "summary, and that starts to cost as soon as releases add up."
                ),
            ),
        ),
    ]


def _accounting() -> list[Slide]:
    eyebrow = "Privacy accounting"
    return [
        Statement(
            "accounting",
            eyebrow,
            "Every release spends privacy",
            "Accounting adds up the loss of every release on the same data, and stops before the budget is spent.",
        ),
        PlotSlide(
            "compose-pure",
            eyebrow,
            "Two releases under ε",
            plots.compose_pure(),
            (
                Say("Publish the count twice, each time with fresh noise."),
                Def("Laplace noise of scale *b*", (Eq("*ε* = Δ / *b*"), Eq("(Δ + Δ) / *b* = 2*ε*"))),
                Say("The worst case is as if one release had sensitivity Δ + Δ: covering blue now takes a lift of 2ε."),
                Say("Under pure ε the budgets add: *k* releases cost *kε*."),
            ),
        ),
        PlotSlide(
            "compose-approx",
            eyebrow,
            "Two releases under (ε, δ)",
            plots.compose_approx(),
            (
                Say("Add the two counts: the total shifts by 2Δ, the noise variance adds to 2*σ*²."),
                Def("δ depends on Δ/σ", (Eq(GAUSSIAN_DELTA, "s"), Eq("2Δ / (√2 *σ*) = √2 · Δ/*σ*", "s"))),
                Tight(
                    (
                        Stat(
                            f"{2 * plots.DELTA_1:.2f}",
                            f"the adding rule: (2ε, 2δ) = (2, {2 * plots.DELTA_1:.2f})",
                        ),
                        Stat(f"{plots.DELTA_2:.2f}", "the area really left uncovered at ε = 2"),
                    )
                ),
                Note("Adding ε and δ charges too much, and more with every release."),
            ),
        ),
    ]


def _concentrated() -> list[Slide]:
    eyebrow = "Concentrated definitions"
    basic, advanced, zc = plots.cost_totals()
    return [
        PlotSlide(
            "cdp",
            eyebrow,
            "Concentrated differential privacy",
            plots.cdp(),
            (
                Def(
                    "(μ, τ)-concentrated differential privacy",
                    (
                        Tight((Eq("E[*L*] ≤ *μ*"), Eq("*L* − E[*L*] is *τ*-subgaussian"))),
                        Note("subgaussian: tails no heavier than a Gaussian with standard deviation *τ*"),
                    ),
                ),
                Say("Describe the bell itself: its centre is at most μ, and it spreads no wider than τ."),
                Say("Gaussian noise: μ = Δ²/(2σ²) and τ = Δ/σ."),
            ),
        ),
        PlotSlide(
            "zcdp",
            eyebrow,
            "Zero-concentrated differential privacy",
            plots.zcdp(),
            (
                Def(
                    "ρ-zero-concentrated differential privacy",
                    (
                        Eq("*D*_{*α*}(*M*(*D*) ‖ *M*(*D′*)) ≤ *ρα*"),
                        Note(
                            "for every order *α* > 1 of the Rényi divergence, a family of distances "
                            "between the two curves"
                        ),
                    ),
                ),
                Say("One number fixes the whole bell: no worse than a Gaussian with mean ρ and variance 2ρ."),
                Say("Gaussian noise: ρ = Δ²/(2σ²). The earlier pictures, with σ = Δ, have ρ = 0.5."),
            ),
        ),
        PlotSlide(
            "composition",
            eyebrow,
            "Composition adds the losses",
            plots.composition(),
            (
                Def("The loss of *k* releases", (Eq("*L* = *L*_{1} + *L*_{2} + … + *L*_{*k*}"),)),
                Say("Sums of bells are bells. The centre grows like *k*, the width only like √*k*."),
                Say(
                    "In zero-concentrated accounting ρ simply adds: *k* releases at ρ each cost *k*ρ. "
                    "Here ρ = 0.125 per release."
                ),
            ),
        ),
        TableSlide(
            "rules",
            eyebrow,
            "Composition rules",
            ("Definition", "One release", "k releases", "ε grows like"),
            (25, 15, 36, 24),
            (
                ("Pure ε", "ε₀", "kε₀", "k"),
                ("(ε, δ), basic rule", "(ε₀, δ₀)", "(kε₀, kδ₀)", "k"),
                ("(ε, δ), advanced rule", "(ε₀, δ₀)", "≈ (ε₀ √(2k ln(1/δ′)), kδ₀ + δ′)", "√k, for small ε₀"),
                ("(μ, τ)-concentrated", "(μ, τ)", "(kμ, √k τ)", "√k, after conversion"),
                ("ρ-zero-concentrated", "ρ", "kρ", "√k, after conversion"),
            ),
            Def(
                "Back to (ε, δ), once, at the end",
                (
                    Eq("*ε* = *ρ* + 2√(*ρ* ln(1/*δ*))"),
                    Note(
                        "A ρ-zero-concentrated mechanism satisfies this (ε, δ) for every δ, so add all "
                        "the ρ first and convert the total."
                    ),
                ),
            ),
        ),
        PlotSlide(
            "cost",
            eyebrow,
            f"The cost of {plots.COST_RELEASES} releases",
            plots.cost(),
            (
                Say("Gaussian noise with σ = 50Δ at every release, and δ = 1/1,000,000 in total."),
                Def(
                    f"Total ε after {plots.COST_RELEASES} releases",
                    (
                        Stat(f"{basic:.1f}", "(ε, δ) with the basic rule"),
                        Stat(f"{advanced:.1f}", "(ε, δ) with the advanced rule"),
                        Stat(f"{zc:.1f}", "zero-concentrated accounting"),
                    ),
                ),
                Say("Same noise, same releases. Only the bookkeeping changes."),
            ),
            flush=False,
        ),
        CardsSlide(
            "recap",
            "Recap",
            "Four definitions, one picture",
            (
                Card(
                    "Pure",
                    "The loss never passes ε.",
                    scene=plots.recap_pure(),
                    tag="*k* releases",
                    footer=Eq("*kε*", "s"),
                ),
                Card(
                    "Approximate",
                    "The stretched curve covers all but δ of the probability.",
                    scene=plots.recap_approx(),
                    tag="*k* releases",
                    footer=Eq("(*kε*, *kδ*)", "s"),
                ),
                Card(
                    "Concentrated",
                    "The loss fits a Gaussian yardstick with centre μ and width τ.",
                    scene=plots.recap_concentrated(),
                    tag="*k* releases",
                    footer=Eq("(*kμ*, √*k* *τ*)", "s"),
                ),
                Card(
                    "Zero-concentrated",
                    "One number for the whole bell: mean ρ, variance 2ρ.",
                    scene=plots.recap_zcdp(),
                    tag="*k* releases",
                    footer=Eq("*kρ*", "s"),
                ),
            ),
            "Same noise, tighter bookkeeping: add up ρ, convert to (ε, δ) once.",
            compact=True,
            background="paper-2",
        ),
    ]


SECTIONS = (
    Section(
        "why",
        "cover",
        "Why releasing statistics needs a privacy definition, and what differential privacy promises.",
    ),
    Section(
        "basics",
        "sensitivity",
        "Sensitivity, noise, ε-DP and (ε, δ)-DP, built up on one plot: the curve on D′ stretched by e^ε "
        "must cover the curve on D, and δ is the area it leaves uncovered.",
    ),
    Section(
        "loss",
        "loss-distribution",
        "The privacy loss distribution, and why one mechanism has a whole curve of (ε, δ) pairs.",
    ),
    Section(
        "accounting",
        "accounting",
        "Privacy accounting: what two releases cost under ε and under (ε, δ), and why adding the "
        "parameters charges too much.",
    ),
    Section(
        "concentrated",
        "cdp",
        "Concentrated and zero-concentrated differential privacy: definitions that describe the whole "
        "privacy loss, how they compose, and what that saves over 200 releases.",
    ),
)


def build_deck() -> Deck:
    slides = [*_why(), *_basics(), *_loss(), *_accounting(), *_concentrated()]
    return Deck("Differential Privacy and Privacy Accounting", tuple(slides), SECTIONS)
