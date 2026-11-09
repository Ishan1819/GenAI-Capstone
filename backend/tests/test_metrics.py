"""Unit tests for the evaluation maths (Eq. (5), RAGAS context precision, Cohen's kappa, Spearman's rho)."""
import pytest

from app.evaluation import metrics
from app.rag.chat import _supporting


def test_hit_and_answered_rate():
    rows = [{"hit": True, "answered": True}, {"hit": False, "answered": True},
            {"hit": True, "answered": False}, {"hit": False, "answered": False}]
    assert metrics.hit_rate(rows) == 0.5
    assert metrics.answered_rate(rows) == 0.5


def test_judge_scores_only_over_answered():
    rows = [{"answered": True, "faithfulness": 1}, {"answered": True, "faithfulness": 0},
            {"answered": False, "faithfulness": None}]
    assert metrics.mean_over_answered(rows, "faithfulness") == 0.5


def test_exact_set_match():
    assert metrics.exact_set_match(["Riya Nair", "arjun  rao"], ["Arjun Rao", "riya nair"])
    assert not metrics.exact_set_match(["Riya Nair"], ["Riya Nair", "Arjun Rao"])


def test_average_precision():
    assert metrics.average_precision([True, False, True]) == pytest.approx((1 + 2 / 3) / 2)
    assert metrics.average_precision([False, True]) == pytest.approx(0.5)
    assert metrics.average_precision([False, False]) == 0.0


def test_cohen_kappa():
    assert metrics.cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == pytest.approx(1.0)
    # textbook example: po = 0.7, pe = 0.5 -> kappa = 0.4
    a = [1] * 5 + [0] * 5
    b = [1] * 4 + [0] + [1] * 2 + [0] * 3
    assert metrics.cohen_kappa(a, b) == pytest.approx(0.4)


def test_spearman_rho():
    assert metrics.spearman_rho([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert metrics.spearman_rho([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert metrics.spearman_rho([5, 5, 4, 3], [5, 4, 4, 3]) == pytest.approx(3.75 / 4.5)
    assert metrics.spearman_rho([5, 5, 5], [1, 2, 3]) is None


def test_guardrail_word_overlap_credit():
    """Eq. (3) fallback: an uncited grounded answer is credited to a top-2 source with >= 35% content-word overlap."""
    ctx = [{"text": "The Cloud and DevOps track covers Linux, Docker, Kubernetes and Terraform."},
           {"text": "Chapters run in Pune and Mumbai."}]
    assert _supporting("The track covers Docker, Kubernetes and Terraform.", ctx) == [1]
    assert _supporting("Hostel refunds take seven days.", ctx) == []
