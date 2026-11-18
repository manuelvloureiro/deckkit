"""The mathematics behind every curve and number in the deck. Nothing here is sampled."""

from __future__ import annotations

import math


def linspace(start: float, stop: float, steps: int) -> list[float]:
    """`steps + 1` evenly spaced values from `start` to `stop`, both included."""
    return [start + (stop - start) * i / steps for i in range(steps + 1)]


def laplace_pdf(y: float, centre: float, scale: float = 1.0) -> float:
    """Density of Laplace noise of the given scale around `centre`."""
    return math.exp(-abs(y - centre) / scale) / (2 * scale)


def normal_pdf(y: float, centre: float, sd: float = 1.0) -> float:
    """Density of Gaussian noise with standard deviation `sd` around `centre`."""
    return math.exp(-((y - centre) ** 2) / (2 * sd * sd)) / (sd * math.sqrt(2 * math.pi))


def normal_cdf(x: float) -> float:
    """Area under a standard bell left of `x`."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def gaussian_delta(eps: float, ratio: float) -> float:
    """Exact delta of the Gaussian mechanism at `eps`, where `ratio` is sensitivity over sigma.

    This is the area of the curve on D that the curve on D', multiplied by e^eps, leaves uncovered.
    """
    return normal_cdf(ratio / 2 - eps / ratio) - math.exp(eps) * normal_cdf(-ratio / 2 - eps / ratio)


def gaussian_epsilon(delta: float, ratio: float) -> float:
    """Smallest eps at which the Gaussian mechanism is (eps, delta)-private, by bisection."""
    low, high = 0.0, 200.0
    for _ in range(200):
        mid = (low + high) / 2
        if gaussian_delta(mid, ratio) > delta:
            low = mid
        else:
            high = mid
    return high


def basic_composition_epsilon(releases: int, ratio: float, delta: float) -> float:
    """Total eps of `releases` Gaussian releases when eps and delta are simply added."""
    return releases * gaussian_epsilon(delta / releases, ratio)


def advanced_composition_epsilon(releases: int, ratio: float, delta: float) -> float:
    """Total eps under the advanced composition theorem, half of delta spent on the theorem's slack."""
    per_release = gaussian_epsilon(delta / (2 * releases), ratio)
    slack = delta / 2
    return per_release * math.sqrt(2 * releases * math.log(1 / slack)) + releases * per_release * (
        math.exp(per_release) - 1
    )


def zcdp_epsilon(releases: int, ratio: float, delta: float) -> float:
    """Total eps when rho is added over the releases and converted to (eps, delta) once."""
    rho = releases * ratio * ratio / 2
    return rho + 2 * math.sqrt(rho * math.log(1 / delta))


def loss_tail(eps: float, mean: float, sd: float) -> float:
    """Probability that a normal privacy loss exceeds `eps`."""
    return 1 - normal_cdf((eps - mean) / sd)
