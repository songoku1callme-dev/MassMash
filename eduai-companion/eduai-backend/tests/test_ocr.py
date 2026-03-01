"""Tests for the OCR/Math-Solver service."""

import pytest
from app.services.ocr_solver import MathSolver


def test_solve_linear_equation():
    result = MathSolver.solve_equation("2*x + 3 = 7")
    assert result["variable"] == "x"
    assert result["solution"] is not None
    # x = 2
    solutions = result["solution"]
    assert "2" in str(solutions)
    assert result["latex"] is not None


def test_solve_quadratic_equation():
    result = MathSolver.solve_equation("x^2 - 4 = 0")
    assert result["variable"] == "x"
    solutions = result["solution"]
    assert len(solutions) == 2
    # x = -2 or x = 2
    sol_set = {str(s) for s in solutions}
    assert "2" in sol_set
    assert "-2" in sol_set


def test_solve_quadratic_formula():
    result = MathSolver.solve_equation("x^2 + 2x + 1 = 0")
    assert result["variable"] == "x"
    solutions = result["solution"]
    # x = -1 (double root)
    assert "-1" in str(solutions)


def test_extract_equations():
    text = "Solve 2x + 3 = 7. Also find x^2 - 4 = 0."
    equations = MathSolver.extract_equations(text)
    assert len(equations) >= 1


def test_extract_no_equations():
    text = "This is just plain text with no math."
    equations = MathSolver.extract_equations(text)
    assert len(equations) == 0


def test_generate_steps():
    result = MathSolver.solve_equation("2*x + 3 = 7")
    steps = result["steps"]
    assert len(steps) >= 2
    # Should contain "Gegeben" and solution
    assert any("Gegeben" in s for s in steps)
    assert any("Loesung" in s or "Loesungen" in s for s in steps)


def test_format_response():
    equations = ["2*x + 3 = 7"]
    results = [MathSolver.solve_equation(eq) for eq in equations]
    formatted = MathSolver.format_response("2x + 3 = 7", equations, results)
    assert "OCR Ergebnis" in formatted
    assert "Loesungsweg" in formatted
    assert "Ergebnis" in formatted


def test_solve_from_text():
    result = MathSolver.solve_from_text("x^2 - 9 = 0")
    assert "formatted_response" in result
    assert "equations" in result
    assert len(result["equations"]) >= 1
    assert "results" in result


def test_solve_invalid_equation():
    result = MathSolver.solve_equation("not a real equation = ???")
    # Should not crash, returns error or empty solution
    assert "equation" in result


def test_prepare_sympy_expr():
    # Test that 2x becomes 2*x
    prepared = MathSolver._prepare_sympy_expr("2x + 3")
    assert "*" in prepared
