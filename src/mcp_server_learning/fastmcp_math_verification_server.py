#!/usr/bin/env python3
"""
FastMCP-powered Mathematical Verification Server

A server for verifying mathematical expressions and multi-step proofs using SymPy.
Focused on calculus, analysis, and linear algebra with LaTeX input support.
"""

import sys
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from fastmcp import FastMCP
import sympy as sp
from sympy import symbols, Symbol, Expr, Matrix, simplify, expand, factor, cancel
from sympy import diff, integrate, limit, series
from sympy import sin, cos, tan, exp, log, sqrt, pi, E, I, oo
from sympy.parsing.latex import parse_latex


# Initialize FastMCP instance
mcp = FastMCP("Mathematical Verification Server")


class LaTeXParser:
    """Parser for converting LaTeX mathematical expressions to SymPy objects."""

    def __init__(self):
        """Initialize the LaTeX parser."""
        pass

    @staticmethod
    def parse(latex_expr: str) -> Union[Expr, Matrix]:
        """Parse a LaTeX expression into a SymPy expression.

        Args:
            latex_expr: LaTeX mathematical expression

        Returns:
            SymPy expression or Matrix

        Raises:
            ValueError: If parsing fails
        """
        try:
            # Clean up the LaTeX expression
            latex_expr = latex_expr.strip()

            # Remove display math delimiters if present
            latex_expr = re.sub(r'^\\\[|\\\]$', '', latex_expr)
            latex_expr = re.sub(r'^\$\$|\$\$$', '', latex_expr)
            latex_expr = re.sub(r'^\$|\$$', '', latex_expr)

            # Preprocess to ensure proper LaTeX function notation
            # Replace common function names with LaTeX commands if not already present
            function_replacements = {
                r'\bsin\b': r'\\sin',
                r'\bcos\b': r'\\cos',
                r'\btan\b': r'\\tan',
                r'\blog\b': r'\\ln',  # Assume natural log
                r'\bexp\b': r'\\exp',
                r'\bsqrt\b': r'\\sqrt',
            }

            for pattern, replacement in function_replacements.items():
                # Only replace if not already a LaTeX command
                if not re.search(replacement, latex_expr):
                    latex_expr = re.sub(pattern, replacement, latex_expr)

            # Try latex2sympy2 first as it's more robust for function notation
            try:
                from latex2sympy2 import latex2sympy
                result = latex2sympy(latex_expr)
                return result
            except ImportError:
                pass
            except Exception:
                pass

            # Fallback to SymPy's LaTeX parser
            try:
                result = parse_latex(latex_expr)
                return result
            except Exception as e:
                raise ValueError(f"Failed to parse LaTeX expression: {str(e)}")

        except Exception as e:
            raise ValueError(f"Error parsing LaTeX: {str(e)}")

    @staticmethod
    def parse_with_context(latex_expr: str, assumptions: List[str] = None) -> Tuple[Union[Expr, Matrix], Dict[Symbol, Any]]:
        """Parse LaTeX with context about variable assumptions.

        Args:
            latex_expr: LaTeX mathematical expression
            assumptions: List of assumptions about variables (e.g., "x is real", "n is positive integer")

        Returns:
            Tuple of (parsed expression, symbol assumptions dict)
        """
        if assumptions is None:
            assumptions = []

        expr = LaTeXParser.parse(latex_expr)

        # Parse assumptions
        symbol_assumptions = {}
        for assumption in assumptions:
            # Simple pattern matching for common assumptions
            # e.g., "x is real", "n is positive", "x > 0"
            match = re.match(r'(\w+)\s+is\s+(\w+)', assumption)
            if match:
                var_name, property_name = match.groups()
                if var_name in str(expr):
                    symbol_assumptions[var_name] = property_name

        return expr, symbol_assumptions


class SymPyVerifier:
    """Core verification engine using SymPy for symbolic mathematics."""

    def __init__(self):
        """Initialize the verifier."""
        pass

    @staticmethod
    def verify_equality(expr1: Union[str, Expr], expr2: Union[str, Expr],
                       assumptions: List[str] = None) -> Dict[str, Any]:
        """Verify if two expressions are mathematically equal.

        Args:
            expr1: First expression (LaTeX string or SymPy expression)
            expr2: Second expression (LaTeX string or SymPy expression)
            assumptions: Optional list of assumptions about variables

        Returns:
            Dict with verification result and details
        """
        try:
            # Parse expressions if they're strings
            if isinstance(expr1, str):
                expr1 = LaTeXParser.parse(expr1)
            if isinstance(expr2, str):
                expr2 = LaTeXParser.parse(expr2)

            # Check if expressions are equal
            difference = simplify(expr1 - expr2)
            is_equal = difference == 0

            return {
                "is_valid": is_equal,
                "expr1": str(expr1),
                "expr2": str(expr2),
                "difference": str(difference),
                "simplified_difference": str(simplify(difference)),
                "explanation": "Expressions are equal" if is_equal else f"Expressions differ by: {difference}"
            }

        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e),
                "explanation": f"Verification failed: {str(e)}"
            }

    @staticmethod
    def verify_derivative(expr: Union[str, Expr], variable: str,
                         expected_result: Union[str, Expr]) -> Dict[str, Any]:
        """Verify a derivative computation.

        Args:
            expr: Expression to differentiate (LaTeX or SymPy)
            variable: Variable to differentiate with respect to
            expected_result: Expected derivative result

        Returns:
            Dict with verification result
        """
        try:
            # Parse inputs
            if isinstance(expr, str):
                expr = LaTeXParser.parse(expr)
            if isinstance(expected_result, str):
                expected_result = LaTeXParser.parse(expected_result)

            # Compute derivative
            var_symbol = symbols(variable)
            computed_derivative = diff(expr, var_symbol)

            # Verify
            difference = simplify(computed_derivative - expected_result)
            is_correct = difference == 0

            return {
                "is_valid": is_correct,
                "original_expr": str(expr),
                "variable": variable,
                "computed_derivative": str(computed_derivative),
                "expected_derivative": str(expected_result),
                "difference": str(difference),
                "explanation": "Derivative is correct" if is_correct else f"Derivative differs by: {difference}"
            }

        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e),
                "explanation": f"Derivative verification failed: {str(e)}"
            }

    @staticmethod
    def verify_integral(expr: Union[str, Expr], variable: str,
                       expected_result: Union[str, Expr],
                       definite: bool = False,
                       limits: Tuple[Any, Any] = None) -> Dict[str, Any]:
        """Verify an integral computation.

        Args:
            expr: Expression to integrate
            variable: Variable to integrate with respect to
            expected_result: Expected integral result
            definite: Whether this is a definite integral
            limits: Tuple of (lower_limit, upper_limit) for definite integrals

        Returns:
            Dict with verification result
        """
        try:
            # Parse inputs
            if isinstance(expr, str):
                expr = LaTeXParser.parse(expr)
            if isinstance(expected_result, str):
                expected_result = LaTeXParser.parse(expected_result)

            # Compute integral
            var_symbol = symbols(variable)

            if definite and limits:
                computed_integral = integrate(expr, (var_symbol, limits[0], limits[1]))
            else:
                computed_integral = integrate(expr, var_symbol)

            # For indefinite integrals, compare derivatives (since constants can differ)
            if not definite:
                # Verify by taking derivative of both results
                derivative_computed = simplify(diff(computed_integral, var_symbol))
                derivative_expected = simplify(diff(expected_result, var_symbol))
                difference = simplify(derivative_computed - derivative_expected)
                is_correct = difference == 0

                explanation = "Integral is correct (derivatives match)" if is_correct else f"Integrals differ (derivative difference: {difference})"
            else:
                # For definite integrals, compare values directly
                difference = simplify(computed_integral - expected_result)
                is_correct = difference == 0
                explanation = "Definite integral is correct" if is_correct else f"Integral differs by: {difference}"

            return {
                "is_valid": is_correct,
                "original_expr": str(expr),
                "variable": variable,
                "computed_integral": str(computed_integral),
                "expected_integral": str(expected_result),
                "definite": definite,
                "limits": str(limits) if limits else None,
                "explanation": explanation
            }

        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e),
                "explanation": f"Integral verification failed: {str(e)}"
            }

    @staticmethod
    def verify_limit(expr: Union[str, Expr], variable: str,
                    point: Union[str, float, int],
                    expected_result: Union[str, Expr],
                    direction: str = "+-") -> Dict[str, Any]:
        """Verify a limit computation.

        Args:
            expr: Expression to take limit of
            variable: Variable approaching the point
            point: Point to approach (can be 'oo' for infinity)
            expected_result: Expected limit result
            direction: Direction of approach ('+', '-', or '+-' for both)

        Returns:
            Dict with verification result
        """
        try:
            # Parse inputs
            if isinstance(expr, str):
                expr = LaTeXParser.parse(expr)
            if isinstance(expected_result, str):
                expected_result = LaTeXParser.parse(expected_result)

            # Handle infinity
            if point == 'oo' or point == 'inf':
                point = sp.oo
            elif point == '-oo' or point == '-inf':
                point = -sp.oo

            # Compute limit
            var_symbol = symbols(variable)
            computed_limit = limit(expr, var_symbol, point, dir=direction)

            # Verify
            difference = simplify(computed_limit - expected_result)
            is_correct = difference == 0

            return {
                "is_valid": is_correct,
                "original_expr": str(expr),
                "variable": variable,
                "point": str(point),
                "direction": direction,
                "computed_limit": str(computed_limit),
                "expected_limit": str(expected_result),
                "difference": str(difference),
                "explanation": "Limit is correct" if is_correct else f"Limit differs by: {difference}"
            }

        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e),
                "explanation": f"Limit verification failed: {str(e)}"
            }

    @staticmethod
    def simplify_expression(expr: Union[str, Expr],
                          show_steps: bool = True) -> Dict[str, Any]:
        """Simplify a mathematical expression.

        Args:
            expr: Expression to simplify
            show_steps: Whether to show intermediate simplification steps

        Returns:
            Dict with simplified expression and steps
        """
        try:
            # Parse expression
            if isinstance(expr, str):
                expr = LaTeXParser.parse(expr)

            # Perform various simplifications
            steps = []

            # Original
            steps.append({"step": "Original", "expression": str(expr)})

            # Expand
            expanded = expand(expr)
            if expanded != expr:
                steps.append({"step": "Expanded", "expression": str(expanded)})

            # Factor
            factored = factor(expr)
            if factored != expr:
                steps.append({"step": "Factored", "expression": str(factored)})

            # Simplify
            simplified = simplify(expr)
            steps.append({"step": "Simplified", "expression": str(simplified)})

            # Cancel (for rational functions)
            try:
                cancelled = cancel(expr)
                if cancelled != simplified:
                    steps.append({"step": "Cancelled", "expression": str(cancelled)})
            except:
                pass

            return {
                "original": str(expr),
                "simplified": str(simplified),
                "steps": steps if show_steps else None,
                "explanation": f"Expression simplified from {expr} to {simplified}"
            }

        except Exception as e:
            return {
                "error": str(e),
                "explanation": f"Simplification failed: {str(e)}"
            }


class ProofStepValidator:
    """Validator for multi-step mathematical proofs."""

    def __init__(self):
        """Initialize the proof validator."""
        self.verifier = SymPyVerifier()

    def validate_proof(self, steps: List[Dict[str, str]],
                      assumptions: List[str] = None) -> Dict[str, Any]:
        """Validate a multi-step proof.

        Args:
            steps: List of proof steps, each containing 'expression', 'justification', and optionally 'result'
            assumptions: Optional list of assumptions

        Returns:
            Dict with validation results for each step
        """
        if assumptions is None:
            assumptions = []

        results = []
        all_valid = True

        for i, step in enumerate(steps):
            step_num = i + 1

            try:
                # Parse current step
                current_expr = step.get("expression")
                justification = step.get("justification", "")
                expected_result = step.get("result")

                step_result = {
                    "step_number": step_num,
                    "expression": current_expr,
                    "justification": justification,
                    "is_valid": None,
                    "explanation": ""
                }

                # If there's an expected result, verify it
                if expected_result:
                    verification = self.verifier.verify_equality(
                        current_expr, expected_result, assumptions
                    )
                    step_result["is_valid"] = verification["is_valid"]
                    step_result["explanation"] = verification["explanation"]

                    if not verification["is_valid"]:
                        all_valid = False

                # Check if this step follows from the previous step
                if i > 0:
                    previous_expr = steps[i - 1].get("result") or steps[i - 1].get("expression")

                    # Determine verification type based on justification
                    if "derivative" in justification.lower() or "differentiate" in justification.lower():
                        # Extract variable from justification if possible
                        var_match = re.search(r'with respect to (\w+)', justification)
                        if var_match:
                            variable = var_match.group(1)
                        else:
                            variable = 'x'  # default

                        verification = self.verifier.verify_derivative(
                            previous_expr, variable, current_expr
                        )
                        step_result["transition_valid"] = verification["is_valid"]
                        step_result["transition_explanation"] = verification["explanation"]

                        if not verification["is_valid"]:
                            all_valid = False

                    elif "integrate" in justification.lower() or "integral" in justification.lower():
                        var_match = re.search(r'with respect to (\w+)', justification)
                        if var_match:
                            variable = var_match.group(1)
                        else:
                            variable = 'x'

                        verification = self.verifier.verify_integral(
                            previous_expr, variable, current_expr
                        )
                        step_result["transition_valid"] = verification["is_valid"]
                        step_result["transition_explanation"] = verification["explanation"]

                        if not verification["is_valid"]:
                            all_valid = False

                    else:
                        # Generic equivalence check
                        verification = self.verifier.verify_equality(
                            previous_expr, current_expr, assumptions
                        )
                        step_result["transition_valid"] = verification["is_valid"]
                        step_result["transition_explanation"] = verification["explanation"]

                        if not verification["is_valid"]:
                            all_valid = False

                results.append(step_result)

            except Exception as e:
                results.append({
                    "step_number": step_num,
                    "expression": step.get("expression", ""),
                    "is_valid": False,
                    "error": str(e),
                    "explanation": f"Step validation failed: {str(e)}"
                })
                all_valid = False

        return {
            "all_steps_valid": all_valid,
            "total_steps": len(steps),
            "valid_steps": sum(1 for r in results if r.get("is_valid") != False),
            "steps": results,
            "assumptions": assumptions
        }


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool
def verify_step(expression: str, expected_result: str,
               assumptions: List[str] = None,
               operation: str = "equality") -> str:
    """Verify a single mathematical step.

    Args:
        expression: Mathematical expression in LaTeX format (e.g., "\\frac{d}{dx}(x^2)")
        expected_result: Expected result in LaTeX format (e.g., "2x")
        assumptions: Optional list of assumptions (e.g., ["x is real"])
        operation: Type of operation - "equality", "derivative", "integral", or "limit"

    Examples:
        verify_step("x^2 + 2x + 1", "(x+1)^2", operation="equality")
        verify_step("x^2", "2x", operation="derivative")
    """
    if assumptions is None:
        assumptions = []

    try:
        verifier = SymPyVerifier()

        if operation == "equality":
            result = verifier.verify_equality(expression, expected_result, assumptions)
        elif operation == "derivative":
            # Extract variable (default to 'x')
            result = verifier.verify_derivative(expression, 'x', expected_result)
        elif operation == "integral":
            result = verifier.verify_integral(expression, 'x', expected_result)
        elif operation == "limit":
            result = verifier.verify_limit(expression, 'x', 'oo', expected_result)
        else:
            return f"Unknown operation type: {operation}"

        # Format response
        if result.get("is_valid"):
            response = f"✓ **Verification Successful**\n\n{result.get('explanation', '')}\n\n"
            response += f"**Expression:** {result.get('expr1', expression)}\n"
            response += f"**Result:** {result.get('expr2', expected_result)}"
        else:
            response = f"✗ **Verification Failed**\n\n{result.get('explanation', '')}\n\n"
            if 'error' not in result:
                response += f"**Expression:** {result.get('expr1', expression)}\n"
                response += f"**Expected:** {result.get('expr2', expected_result)}\n"
                if 'difference' in result:
                    response += f"**Difference:** {result['difference']}"

        return response

    except Exception as e:
        return f"Error verifying step: {str(e)}"


@mcp.tool
def verify_proof(steps: List[Dict[str, str]], assumptions: List[str] = None) -> str:
    """Verify a multi-step mathematical proof.

    Args:
        steps: List of proof steps. Each step should be a dict with:
               - 'expression': The mathematical expression (LaTeX)
               - 'justification': Reason for this step
               - 'result' (optional): Expected result after this step
        assumptions: Optional list of assumptions about variables

    Example:
        steps = [
            {"expression": "\\int x dx", "result": "\\frac{x^2}{2} + C", "justification": "Power rule for integration"},
            {"expression": "\\frac{d}{dx}(\\frac{x^2}{2} + C)", "result": "x", "justification": "Differentiate with respect to x"}
        ]
    """
    if assumptions is None:
        assumptions = []

    try:
        validator = ProofStepValidator()
        result = validator.validate_proof(steps, assumptions)

        # Format response
        response = f"# Proof Verification Results\n\n"
        response += f"**Total Steps:** {result['total_steps']}\n"
        response += f"**Valid Steps:** {result['valid_steps']}/{result['total_steps']}\n"
        response += f"**Overall Status:** {'✓ Valid' if result['all_steps_valid'] else '✗ Invalid'}\n\n"

        if assumptions:
            response += f"**Assumptions:** {', '.join(assumptions)}\n\n"

        response += "## Step-by-Step Analysis\n\n"

        for step_result in result['steps']:
            step_num = step_result['step_number']
            response += f"### Step {step_num}\n"
            response += f"**Expression:** {step_result['expression']}\n"
            response += f"**Justification:** {step_result.get('justification', 'N/A')}\n"

            if 'is_valid' in step_result and step_result['is_valid'] is not None:
                status = "✓" if step_result['is_valid'] else "✗"
                response += f"**Status:** {status}\n"

            if 'explanation' in step_result:
                response += f"**Explanation:** {step_result['explanation']}\n"

            if 'transition_valid' in step_result:
                trans_status = "✓" if step_result['transition_valid'] else "✗"
                response += f"**Transition from previous step:** {trans_status}\n"
                response += f"**Transition explanation:** {step_result.get('transition_explanation', '')}\n"

            if 'error' in step_result:
                response += f"**Error:** {step_result['error']}\n"

            response += "\n"

        return response

    except Exception as e:
        return f"Error verifying proof: {str(e)}"


@mcp.tool
def simplify_expression(expression: str, show_steps: bool = True) -> str:
    """Simplify a mathematical expression and optionally show steps.

    Args:
        expression: Mathematical expression in LaTeX format
        show_steps: Whether to show intermediate simplification steps

    Example:
        simplify_expression("\\frac{x^2 - 1}{x - 1}", show_steps=True)
    """
    try:
        verifier = SymPyVerifier()
        result = verifier.simplify_expression(expression, show_steps)

        if 'error' in result:
            return f"Error: {result['error']}"

        response = f"# Expression Simplification\n\n"
        response += f"**Original:** {result['original']}\n"
        response += f"**Simplified:** {result['simplified']}\n\n"

        if show_steps and result.get('steps'):
            response += "## Simplification Steps\n\n"
            for step in result['steps']:
                response += f"**{step['step']}:** {step['expression']}\n"

        return response

    except Exception as e:
        return f"Error simplifying expression: {str(e)}"


@mcp.tool
def verify_equivalence(expr1: str, expr2: str, assumptions: List[str] = None) -> str:
    """Verify if two mathematical expressions are equivalent.

    Args:
        expr1: First expression in LaTeX format
        expr2: Second expression in LaTeX format
        assumptions: Optional list of assumptions about variables

    Example:
        verify_equivalence("x^2 - 1", "(x-1)(x+1)")
    """
    if assumptions is None:
        assumptions = []

    try:
        verifier = SymPyVerifier()
        result = verifier.verify_equality(expr1, expr2, assumptions)

        if result.get("is_valid"):
            response = f"✓ **Expressions are Equivalent**\n\n"
            response += f"**Expression 1:** {result['expr1']}\n"
            response += f"**Expression 2:** {result['expr2']}\n"
            response += f"**Difference:** {result['simplified_difference']} (simplifies to 0)"
        else:
            response = f"✗ **Expressions are NOT Equivalent**\n\n"
            response += f"**Expression 1:** {result['expr1']}\n"
            response += f"**Expression 2:** {result['expr2']}\n"
            response += f"**Difference:** {result['simplified_difference']}"

        if assumptions:
            response += f"\n\n**Assumptions:** {', '.join(assumptions)}"

        return response

    except Exception as e:
        return f"Error verifying equivalence: {str(e)}"


@mcp.tool
def check_identity(identity_expr: str, variable: str = 'x',
                   test_values: List[float] = None) -> str:
    """Check if a mathematical identity holds.

    Args:
        identity_expr: Identity to check (e.g., "sin(x)^2 + cos(x)^2 - 1")
        variable: Variable in the identity (default: 'x')
        test_values: Optional list of specific values to test

    Example:
        check_identity("sin(x)^2 + cos(x)^2 - 1", variable="x")
        check_identity("e^{i\\pi} + 1", test_values=[])
    """
    try:
        # Parse the identity expression
        expr = LaTeXParser.parse(identity_expr)

        # Simplify to check if it equals zero
        simplified = simplify(expr)

        is_identity = simplified == 0

        response = f"# Identity Verification\n\n"
        response += f"**Identity:** {identity_expr}\n"
        response += f"**Parsed as:** {expr}\n"
        response += f"**Simplified:** {simplified}\n\n"

        if is_identity:
            response += f"✓ **Identity Holds** (simplifies to 0)\n"
        else:
            response += f"✗ **Identity Does NOT Hold**\n"
            response += f"Expression simplifies to: {simplified} (not 0)\n"

        # Test with specific values if provided
        if test_values is not None and len(test_values) > 0:
            response += f"\n## Numerical Verification\n\n"
            var_symbol = symbols(variable)

            for val in test_values:
                try:
                    result = expr.subs(var_symbol, val)
                    result_float = float(result.evalf())
                    status = "✓" if abs(result_float) < 1e-10 else "✗"
                    response += f"**{variable} = {val}:** {result_float} {status}\n"
                except Exception as e:
                    response += f"**{variable} = {val}:** Error - {str(e)}\n"

        return response

    except Exception as e:
        return f"Error checking identity: {str(e)}"


@mcp.tool
def verify_derivative(expression: str, variable: str, expected_derivative: str) -> str:
    """Verify a derivative calculation.

    Args:
        expression: Expression to differentiate (LaTeX format)
        variable: Variable to differentiate with respect to
        expected_derivative: Expected derivative result (LaTeX format)

    Example:
        verify_derivative("x^2", "x", "2x")
        verify_derivative("\\sin(x) \\cos(x)", "x", "\\cos^2(x) - \\sin^2(x)")
    """
    try:
        verifier = SymPyVerifier()
        result = verifier.verify_derivative(expression, variable, expected_derivative)

        response = f"# Derivative Verification\n\n"
        response += f"**Original Expression:** {result['original_expr']}\n"
        response += f"**Variable:** {result['variable']}\n"
        response += f"**Expected Derivative:** {result['expected_derivative']}\n"
        response += f"**Computed Derivative:** {result['computed_derivative']}\n\n"

        if result.get("is_valid"):
            response += f"✓ **Derivative is Correct**\n"
        else:
            response += f"✗ **Derivative is Incorrect**\n"
            response += f"**Difference:** {result.get('difference', 'N/A')}\n"

        response += f"\n{result.get('explanation', '')}"

        return response

    except Exception as e:
        return f"Error verifying derivative: {str(e)}"


@mcp.tool
def verify_integral(expression: str, variable: str, expected_integral: str,
                   is_definite: bool = False,
                   lower_limit: Optional[str] = None,
                   upper_limit: Optional[str] = None) -> str:
    """Verify an integral calculation.

    Args:
        expression: Expression to integrate (LaTeX format)
        variable: Variable to integrate with respect to
        expected_integral: Expected integral result (LaTeX format)
        is_definite: Whether this is a definite integral
        lower_limit: Lower limit for definite integral (LaTeX format or number)
        upper_limit: Upper limit for definite integral (LaTeX format or number)

    Example:
        verify_integral("x", "x", "\\frac{x^2}{2} + C", is_definite=False)
        verify_integral("x", "x", "\\frac{1}{2}", is_definite=True, lower_limit="0", upper_limit="1")
    """
    try:
        verifier = SymPyVerifier()

        # Parse limits if provided
        limits = None
        if is_definite and lower_limit is not None and upper_limit is not None:
            try:
                lower = LaTeXParser.parse(lower_limit) if isinstance(lower_limit, str) else lower_limit
                upper = LaTeXParser.parse(upper_limit) if isinstance(upper_limit, str) else upper_limit
                limits = (lower, upper)
            except:
                # Try as numbers
                lower = float(lower_limit) if lower_limit != 'oo' else sp.oo
                upper = float(upper_limit) if upper_limit != 'oo' else sp.oo
                limits = (lower, upper)

        result = verifier.verify_integral(expression, variable, expected_integral,
                                         definite=is_definite, limits=limits)

        response = f"# Integral Verification\n\n"
        response += f"**Original Expression:** {result['original_expr']}\n"
        response += f"**Variable:** {result['variable']}\n"

        if is_definite:
            response += f"**Type:** Definite Integral\n"
            response += f"**Limits:** {result.get('limits', 'N/A')}\n"
        else:
            response += f"**Type:** Indefinite Integral\n"

        response += f"**Expected Integral:** {result['expected_integral']}\n"
        response += f"**Computed Integral:** {result['computed_integral']}\n\n"

        if result.get("is_valid"):
            response += f"✓ **Integral is Correct**\n"
        else:
            response += f"✗ **Integral is Incorrect**\n"

        response += f"\n{result.get('explanation', '')}"

        return response

    except Exception as e:
        return f"Error verifying integral: {str(e)}"


def main():
    """Run the FastMCP Mathematical Verification server"""
    try:
        print("Starting Mathematical Verification MCP server...", file=sys.stderr)
        mcp.run()
    except Exception as e:
        print(f"Failed to start Mathematical Verification MCP server: {e}", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
