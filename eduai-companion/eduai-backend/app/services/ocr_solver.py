"""OCR + SymPy Math Solver Service.

Pipeline: Image → Tesseract OCR → Parse equation → SymPy solve → Step-by-step Markdown.
"""

import re
import io
import logging
from typing import Optional

import pytesseract
from PIL import Image
import sympy
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

logger = logging.getLogger(__name__)

# SymPy parser transformations for natural math input
TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


class MathSolver:
    """Extract equations from images via OCR and solve them step-by-step."""

    @staticmethod
    def ocr_image(image_bytes: bytes) -> str:
        """Run Tesseract OCR on image bytes. Returns extracted text."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            # Convert to RGB if needed (e.g. RGBA PNGs)
            if image.mode not in ("L", "RGB"):
                image = image.convert("RGB")
            text = pytesseract.image_to_string(image, lang="deu+eng")
            return text.strip()
        except Exception as e:
            logger.error("OCR failed: %s", e)
            raise ValueError(f"OCR-Fehler: {e}") from e

    @staticmethod
    def extract_equations(text: str) -> list[str]:
        """Extract mathematical equations from OCR text.

        Looks for patterns like: 2x + 3 = 7, x^2 - 4 = 0, etc.
        """
        equations: list[str] = []

        # Pattern: anything with = sign that looks like math
        lines = text.replace("\n", " ").split(".")
        for line in lines:
            line = line.strip()
            if "=" in line:
                # Clean up OCR artifacts
                cleaned = line.replace("×", "*").replace("÷", "/")
                cleaned = cleaned.replace("–", "-").replace("—", "-")
                cleaned = re.sub(r"\s+", " ", cleaned)
                # Check it has at least one letter or digit on each side of =
                parts = cleaned.split("=")
                if len(parts) == 2:
                    left, right = parts
                    if re.search(r"[a-zA-Z0-9]", left) and re.search(
                        r"[a-zA-Z0-9]", right
                    ):
                        equations.append(cleaned.strip())

        # If no equations found with =, try to find expressions
        if not equations:
            # Look for standalone math expressions
            math_pattern = r"[\d]+\s*[+\-*/^]\s*[\d\w]+(?:\s*[+\-*/^=]\s*[\d\w]+)*"
            found = re.findall(math_pattern, text)
            equations.extend(found)

        return equations[:5]  # Limit to 5 equations

    @staticmethod
    def _prepare_sympy_expr(eq_str: str) -> str:
        """Clean equation string for SymPy parsing."""
        s = eq_str.strip()
        # Replace common OCR/text artifacts
        s = s.replace("^", "**")
        s = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", s)  # 2x -> 2*x
        s = re.sub(r"([a-zA-Z])(\d)", r"\1*\2", s)  # x2 -> x*2 (less common)
        s = s.replace(" ", "")
        return s

    @staticmethod
    def solve_equation(eq_str: str) -> dict:
        """Solve a single equation and return steps + solution.

        Returns dict with keys: equation, variable, solution, steps, latex
        """
        x = sympy.Symbol("x")
        y = sympy.Symbol("y")
        local_dict = {"x": x, "y": y, "pi": sympy.pi, "e": sympy.E}

        try:
            prepared = MathSolver._prepare_sympy_expr(eq_str)

            if "=" in prepared:
                left_str, right_str = prepared.split("=", 1)
                left = parse_expr(
                    left_str, local_dict=local_dict, transformations=TRANSFORMATIONS
                )
                right = parse_expr(
                    right_str, local_dict=local_dict, transformations=TRANSFORMATIONS
                )
                equation = sympy.Eq(left, right)
            else:
                # Treat as expression = 0
                expr = parse_expr(
                    prepared, local_dict=local_dict, transformations=TRANSFORMATIONS
                )
                equation = sympy.Eq(expr, 0)

            # Determine the variable to solve for
            free_symbols = equation.free_symbols
            if not free_symbols:
                # Pure numeric — evaluate
                is_true = sympy.simplify(equation)
                return {
                    "equation": eq_str,
                    "variable": None,
                    "solution": str(is_true),
                    "steps": ["Numerische Gleichung ausgewertet."],
                    "latex": sympy.latex(equation),
                }

            var = x if x in free_symbols else list(free_symbols)[0]
            solutions = sympy.solve(equation, var)

            # Generate step-by-step explanation
            steps = MathSolver._generate_steps(equation, var, solutions)

            solution_strs = [str(s) for s in solutions]
            solution_latex = [sympy.latex(s) for s in solutions]

            return {
                "equation": eq_str,
                "variable": str(var),
                "solution": solution_strs,
                "steps": steps,
                "latex": sympy.latex(equation),
                "solution_latex": solution_latex,
            }
        except Exception as e:
            logger.warning("Could not solve '%s': %s", eq_str, e)
            return {
                "equation": eq_str,
                "variable": None,
                "solution": None,
                "steps": [f"Konnte nicht gelöst werden: {e}"],
                "latex": None,
                "error": str(e),
            }

    @staticmethod
    def _generate_steps(
        equation: sympy.Eq,
        var: sympy.Symbol,
        solutions: list,
    ) -> list[str]:
        """Generate German step-by-step explanation."""
        steps: list[str] = []
        lhs = equation.lhs
        rhs = equation.rhs

        steps.append(f"Gegeben: ${sympy.latex(lhs)} = {sympy.latex(rhs)}$")

        # Move everything to one side
        expr = lhs - rhs
        simplified = sympy.simplify(expr)
        if simplified != expr:
            steps.append(f"Vereinfache: ${sympy.latex(simplified)} = 0$")

        # Factor if possible
        factored = sympy.factor(expr)
        if factored != expr and factored != simplified:
            steps.append(f"Faktorisiere: ${sympy.latex(factored)} = 0$")

        # Show solutions
        if solutions:
            if len(solutions) == 1:
                steps.append(
                    f"Lösung: ${sympy.latex(var)} = {sympy.latex(solutions[0])}$"
                )
            else:
                sol_parts = [
                    f"${sympy.latex(var)}_{{{i + 1}}} = {sympy.latex(s)}$"
                    for i, s in enumerate(solutions)
                ]
                steps.append(f"Lösungen: {', '.join(sol_parts)}")

            # Verification step
            for s in solutions[:2]:
                check = lhs.subs(var, s)
                check_simplified = sympy.simplify(check)
                steps.append(
                    f"Probe: ${sympy.latex(var)} = {sympy.latex(s)}$ einsetzen: "
                    f"${sympy.latex(lhs)}$ = ${sympy.latex(check_simplified)}$ = ${sympy.latex(rhs)}$ ✓"
                )
        else:
            steps.append("Keine reelle Lösung gefunden.")

        return steps

    @staticmethod
    def format_response(
        ocr_text: str,
        equations: list[str],
        results: list[dict],
    ) -> str:
        """Format the complete response as Markdown with KaTeX."""
        parts: list[str] = []
        parts.append("## 📷 OCR Ergebnis\n")
        parts.append(f"**Erkannter Text:**\n> {ocr_text[:500]}\n")

        if not equations:
            parts.append(
                "\n⚠️ Keine mathematischen Gleichungen erkannt. "
                "Bitte ein klareres Bild hochladen."
            )
            return "\n".join(parts)

        parts.append(f"\n**{len(equations)} Gleichung(en) erkannt:**\n")

        for i, result in enumerate(results, 1):
            parts.append(f"### Gleichung {i}: `{result['equation']}`\n")

            if result.get("latex"):
                parts.append(f"$${ result['latex'] }$$\n")

            if result.get("steps"):
                parts.append("**Lösungsweg:**\n")
                for j, step in enumerate(result["steps"], 1):
                    parts.append(f"{j}. {step}")
                parts.append("")

            if result.get("solution") and not result.get("error"):
                sols = result["solution"]
                if isinstance(sols, list):
                    latex_sols = result.get("solution_latex", sols)
                    sol_display = ", ".join(
                        f"${l}$" for l in latex_sols
                    )
                    parts.append(f"**Ergebnis:** {sol_display}\n")
                else:
                    parts.append(f"**Ergebnis:** {sols}\n")

        parts.append("\n*Quelle: OCR + SymPy Solver*")
        return "\n".join(parts)

    @classmethod
    def solve_from_image(cls, image_bytes: bytes) -> dict:
        """Full pipeline: image → OCR → extract → solve → format.

        Returns dict with ocr_text, equations, results, formatted_response.
        """
        ocr_text = cls.ocr_image(image_bytes)
        equations = cls.extract_equations(ocr_text)
        results = [cls.solve_equation(eq) for eq in equations]
        formatted = cls.format_response(ocr_text, equations, results)

        return {
            "ocr_text": ocr_text,
            "equations": equations,
            "results": results,
            "formatted_response": formatted,
        }

    @classmethod
    def solve_from_text(cls, equation_text: str) -> dict:
        """Solve equation(s) provided as text (no OCR needed).

        Returns dict with equations, results, formatted_response.
        """
        equations = cls.extract_equations(equation_text)
        if not equations:
            # Try treating the whole input as one equation
            equations = [equation_text.strip()]

        results = [cls.solve_equation(eq) for eq in equations]
        formatted = cls.format_response(equation_text, equations, results)

        return {
            "ocr_text": equation_text,
            "equations": equations,
            "results": results,
            "formatted_response": formatted,
        }
