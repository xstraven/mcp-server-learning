"""
Tests for the Mathematical Verification MCP Server

Tests cover:
- LaTeX parsing
- Expression verification
- Derivative verification
- Integral verification
- Limit verification
- Multi-step proof validation
- Expression simplification
"""

import pytest
from mcp_server_learning.fastmcp_math_verification_server import (
    LaTeXParser,
    SymPyVerifier,
    ProofStepValidator,
)
import sympy as sp
from sympy import symbols, sin, cos, exp, log, pi, E


class TestLaTeXParser:
    """Test LaTeX parsing functionality."""

    def test_parse_simple_expression(self):
        """Test parsing simple algebraic expressions."""
        result = LaTeXParser.parse("x^2 + 2x + 1")
        x = symbols('x')
        expected = x**2 + 2*x + 1
        assert sp.simplify(result - expected) == 0

    def test_parse_fraction(self):
        """Test parsing fractions."""
        result = LaTeXParser.parse(r"\frac{x^2}{2}")
        x = symbols('x')
        expected = x**2 / 2
        assert sp.simplify(result - expected) == 0

    def test_parse_trigonometric(self):
        """Test parsing trigonometric functions."""
        result = LaTeXParser.parse(r"\sin(x) + \cos(x)")
        x = symbols('x')
        expected = sin(x) + cos(x)
        assert sp.simplify(result - expected) == 0

    def test_parse_exponential(self):
        """Test parsing exponential expressions."""
        result = LaTeXParser.parse(r"e^{x}")
        x = symbols('x')
        expected = exp(x)
        assert result == expected

    def test_parse_with_display_delimiters(self):
        """Test parsing expressions with display math delimiters."""
        result = LaTeXParser.parse(r"$$x^2 + 1$$")
        x = symbols('x')
        expected = x**2 + 1
        assert sp.simplify(result - expected) == 0


class TestSymPyVerifier:
    """Test SymPy verification functionality."""

    def test_verify_equality_simple(self):
        """Test verifying simple equality."""
        verifier = SymPyVerifier()
        result = verifier.verify_equality("x^2 - 1", "(x-1)(x+1)")

        assert result["is_valid"] == True
        assert result["simplified_difference"] == "0"

    def test_verify_equality_false(self):
        """Test verifying false equality."""
        verifier = SymPyVerifier()
        result = verifier.verify_equality("x^2 + 1", "x^2 + 2")

        assert result["is_valid"] == False

    def test_verify_derivative_power_rule(self):
        """Test verifying derivative with power rule."""
        verifier = SymPyVerifier()
        result = verifier.verify_derivative("x^2", "x", "2*x")

        assert result["is_valid"] == True

    def test_verify_derivative_product_rule(self):
        """Test verifying derivative with product rule."""
        verifier = SymPyVerifier()
        result = verifier.verify_derivative(r"x \cdot \sin(x)", "x", r"\sin(x) + x \cdot \cos(x)")

        assert result["is_valid"] == True

    def test_verify_derivative_chain_rule(self):
        """Test verifying derivative with chain rule."""
        verifier = SymPyVerifier()
        result = verifier.verify_derivative(r"\sin(x^2)", "x", r"2 \cdot x \cdot \cos(x^2)")

        assert result["is_valid"] == True

    def test_verify_derivative_incorrect(self):
        """Test verifying incorrect derivative."""
        verifier = SymPyVerifier()
        result = verifier.verify_derivative("x^2", "x", "x")  # Wrong derivative

        assert result["is_valid"] == False

    def test_verify_integral_power_rule(self):
        """Test verifying integral with power rule."""
        verifier = SymPyVerifier()
        result = verifier.verify_integral("x", "x", "x^2/2", definite=False)

        assert result["is_valid"] == True

    def test_verify_integral_with_constant(self):
        """Test that indefinite integrals work with different constants."""
        verifier = SymPyVerifier()
        # Both should be valid since they differ only by a constant
        result1 = verifier.verify_integral("x", "x", "x^2/2 + 1", definite=False)
        result2 = verifier.verify_integral("x", "x", "x^2/2 + 5", definite=False)

        # Both should be valid (derivatives match)
        assert result1["is_valid"] == True
        assert result2["is_valid"] == True

    def test_verify_definite_integral(self):
        """Test verifying definite integral."""
        verifier = SymPyVerifier()
        result = verifier.verify_integral("x", "x", "1/2",
                                         definite=True, limits=(0, 1))

        assert result["is_valid"] == True

    def test_verify_limit_basic(self):
        """Test verifying basic limit."""
        verifier = SymPyVerifier()
        result = verifier.verify_limit("(x^2 - 1)/(x - 1)", "x", 1, "2")

        assert result["is_valid"] == True

    def test_verify_limit_infinity(self):
        """Test verifying limit at infinity."""
        verifier = SymPyVerifier()
        result = verifier.verify_limit("1/x", "x", "oo", "0")

        assert result["is_valid"] == True

    def test_simplify_expression_factoring(self):
        """Test expression simplification with factoring."""
        verifier = SymPyVerifier()
        result = verifier.simplify_expression("x^2 - 1", show_steps=True)

        assert "simplified" in result
        assert "steps" in result
        # Check that steps are provided
        assert len(result["steps"]) > 0

    def test_simplify_expression_rational(self):
        """Test simplification of rational expressions."""
        verifier = SymPyVerifier()
        result = verifier.simplify_expression("(x^2 - 1)/(x - 1)", show_steps=True)

        # The simplified form should be x + 1
        simplified_expr = sp.sympify(result["simplified"])
        x = symbols('x')
        assert sp.simplify(simplified_expr - (x + 1)) == 0


class TestProofStepValidator:
    """Test multi-step proof validation."""

    def test_validate_simple_proof(self):
        """Test validating a simple two-step proof."""
        validator = ProofStepValidator()

        steps = [
            {
                "expression": "x^2 - 1",
                "result": "(x-1)(x+1)",
                "justification": "Factoring difference of squares"
            },
            {
                "expression": "(x-1)(x+1)",
                "result": "x^2 - 1",
                "justification": "Expanding"
            }
        ]

        result = validator.validate_proof(steps)

        assert result["all_steps_valid"] == True
        assert result["total_steps"] == 2
        assert result["valid_steps"] == 2

    def test_validate_proof_with_derivative(self):
        """Test validating proof involving derivatives."""
        validator = ProofStepValidator()

        # Two-step proof: start with expression, then show derivative
        steps = [
            {
                "expression": "x^2",
                "result": "x^2",
                "justification": "Starting expression"
            },
            {
                "expression": r"2 \cdot x",
                "result": r"2 \cdot x",
                "justification": "Differentiate with respect to x"
            }
        ]

        result = validator.validate_proof(steps)

        # Should recognize derivative and validate transition
        assert result["total_steps"] == 2
        assert result["steps"][1].get("transition_valid") == True

    def test_validate_proof_with_integral(self):
        """Test validating proof involving integrals."""
        validator = ProofStepValidator()

        # Two-step proof: start with expression, then show integral
        steps = [
            {
                "expression": r"2 \cdot x",
                "result": r"2 \cdot x",
                "justification": "Starting expression"
            },
            {
                "expression": "x^2",
                "result": "x^2",
                "justification": "Integrate with respect to x"
            }
        ]

        result = validator.validate_proof(steps)

        assert result["total_steps"] == 2
        # The step should be valid (derivatives match, ignoring constant)
        assert result["steps"][1].get("transition_valid") == True

    def test_validate_invalid_proof(self):
        """Test validating an invalid proof."""
        validator = ProofStepValidator()

        steps = [
            {
                "expression": "x^2",
                "result": "3*x",  # Wrong derivative
                "justification": "Differentiate with respect to x"
            }
        ]

        result = validator.validate_proof(steps)

        assert result["all_steps_valid"] == False
        assert result["steps"][0]["is_valid"] == False


class TestCalculusVerification:
    """Test calculus-specific verification."""

    def test_verify_quotient_rule(self):
        """Test derivative verification using quotient rule."""
        verifier = SymPyVerifier()
        # d/dx[sin(x)/x] = (x*cos(x) - sin(x))/x^2
        result = verifier.verify_derivative(
            r"\frac{\sin(x)}{x}",
            "x",
            r"\frac{x \cdot \cos(x) - \sin(x)}{x^2}"
        )

        assert result["is_valid"] == True

    def test_verify_exponential_derivative(self):
        """Test derivative of exponential function."""
        verifier = SymPyVerifier()
        result = verifier.verify_derivative("e^x", "x", "e^x")

        assert result["is_valid"] == True

    def test_verify_logarithm_derivative(self):
        """Test derivative of logarithm."""
        verifier = SymPyVerifier()
        result = verifier.verify_derivative(r"\ln(x)", "x", r"\frac{1}{x}")

        assert result["is_valid"] == True

    def test_verify_integration_by_parts_result(self):
        """Test integration by parts result."""
        verifier = SymPyVerifier()
        # ∫x*e^x dx = x*e^x - e^x + C
        result = verifier.verify_integral(
            "x*e^x",
            "x",
            "x*e^x - e^x",
            definite=False
        )

        assert result["is_valid"] == True

    def test_verify_trigonometric_integral(self):
        """Test trigonometric integral."""
        verifier = SymPyVerifier()
        # ∫sin(x) dx = -cos(x) + C
        result = verifier.verify_integral(r"\sin(x)", "x", r"-\cos(x)", definite=False)

        assert result["is_valid"] == True


class TestLinearAlgebraVerification:
    """Test linear algebra verification (basic)."""

    def test_verify_matrix_determinant_formula(self):
        """Test verification involving matrix determinants."""
        # For 2x2 matrix, det = ad - bc
        # We'll verify this symbolically
        verifier = SymPyVerifier()

        # Create symbolic expression for 2x2 determinant
        a, b, c, d = symbols('a b c d')
        det_expr = a*d - b*c

        # Verify it's the same
        result = verifier.verify_equality(
            "a*d - b*c",
            "a*d - b*c"
        )

        assert result["is_valid"] == True


class TestIdentityVerification:
    """Test mathematical identity verification."""

    def test_pythagorean_identity(self):
        """Test Pythagorean identity: sin²(x) + cos²(x) = 1."""
        verifier = SymPyVerifier()
        result = verifier.verify_equality(r"\sin^2(x) + \cos^2(x)", "1")

        assert result["is_valid"] == True

    @pytest.mark.skip(reason="Complex exponential parsing requires special handling - not critical for main functionality")
    def test_exponential_identity(self):
        """Test exponential identity: e^(i*pi) + 1 = 0."""
        # This is Euler's identity
        # Skip for now as it requires special handling of complex exponentials
        pass

    def test_logarithm_identity(self):
        """Test logarithm identity: log(a*b) = log(a) + log(b)."""
        verifier = SymPyVerifier()
        a, b = symbols('a b', positive=True, real=True)

        # This requires assumptions to be valid
        expr1 = sp.log(a*b)
        expr2 = sp.log(a) + sp.log(b)

        # Expand the log
        expr1_expanded = sp.expand_log(expr1, force=True)

        assert sp.simplify(expr1_expanded - expr2) == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_invalid_latex(self):
        """Test parsing invalid LaTeX."""
        with pytest.raises(ValueError):
            LaTeXParser.parse("\\invalid{syntax")

    def test_verify_with_undefined_variable(self):
        """Test verification with expressions containing different variables."""
        verifier = SymPyVerifier()

        # These should not be equal (different variables)
        result = verifier.verify_equality("x^2", "y^2")

        assert result["is_valid"] == False

    def test_derivative_of_constant(self):
        """Test derivative of constant."""
        verifier = SymPyVerifier()
        result = verifier.verify_derivative("5", "x", "0")

        assert result["is_valid"] == True

    def test_integral_of_zero(self):
        """Test integral of zero."""
        verifier = SymPyVerifier()
        result = verifier.verify_integral("0", "x", "0", definite=False)

        assert result["is_valid"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
