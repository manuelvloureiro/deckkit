import math

import pytest

from dpdeck import plots
from dpdeck.dpmath import gaussian_delta, gaussian_epsilon, laplace_pdf, loss_tail, normal_cdf


def test_numbers_quoted_on_the_slides() -> None:
    assert plots.DELTA_1 == pytest.approx(0.1269, abs=1e-4)
    assert plots.DELTA_2 == pytest.approx(0.1145, abs=1e-4)
    assert plots.TAIL_1 == pytest.approx(0.3085, abs=1e-4)
    assert [round(gaussian_delta(e, 1.0), 2) for e in (0.5, 1, 2)] == [0.24, 0.13, 0.02]
    assert [round(t, 1) for t in plots.cost_totals()] == [18.9, 9.4, 1.5]


def test_delta_is_the_uncovered_area() -> None:
    """The closed form equals the integral of max(0, p - e^eps q) over the outputs."""
    eps, step = 1.0, 0.001
    area = 0.0
    for i in range(-10000, 20000):
        y = i * step
        p = math.exp(-(y**2) / 2) / math.sqrt(2 * math.pi)
        q = math.exp(-((y - 1) ** 2) / 2) / math.sqrt(2 * math.pi)
        area += max(0.0, p - math.exp(eps) * q) * step
    assert area == pytest.approx(gaussian_delta(eps, 1.0), abs=1e-4)


def test_laplace_ratio_never_exceeds_e_to_eps() -> None:
    worst = max(laplace_pdf(y / 10, 7) / laplace_pdf(y / 10, 8) for y in range(0, 150))
    assert worst == pytest.approx(math.e)


def test_epsilon_inverts_delta() -> None:
    assert gaussian_delta(gaussian_epsilon(1e-6, 0.02), 0.02) == pytest.approx(1e-6, rel=1e-6)
    assert loss_tail(0.5, 0.5, 1.0) == pytest.approx(0.5)
    assert normal_cdf(0) == 0.5
