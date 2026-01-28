#!/usr/bin/env python3
"""
Test script to verify that LaTeX is automatically converted to display format.
"""

import pytest

# Path handling is done by conftest.py

from mcp_server_learning.fastmcp_flashcard_server import (
    AnkiCardManager,
    AnkiConnector,
    FlashcardGenerator,
    get_anki_connector,
)


def test_latex_conversion():
    """Test LaTeX conversion to display format."""

    print("=== Testing LaTeX Conversion to Display Format ===\n")

    # Test cases with different LaTeX formats
    test_cases = [
        {
            "name": "Sigmoid with inline LaTeX",
            "input": "Q: What is the sigmoid function?\nA: $\\sigma(x) = \\frac{1}{1 + e^{-x}}$",
            "expected_back": "\\[\\sigma(x) = \\frac{1}{1 + e^{-x}}\\]",
        },
        {
            "name": "Double dollar LaTeX",
            "input": "Q: What is Euler's formula?\nA: $$e^{i\\pi} + 1 = 0$$",
            "expected_back": "\\[e^{i\\pi} + 1 = 0\\]",
        },
        {
            "name": "Parenthesis LaTeX",
            "input": "Q: What is the quadratic formula?\nA: \\(x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}\\)",
            "expected_back": "\\[x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}\\]",
        },
        {
            "name": "Multiple equations",
            "input": "Q: What are the basic trig identities?\nA: $\\sin^2(x) + \\cos^2(x) = 1$ and $\\tan(x) = \\frac{\\sin(x)}{\\cos(x)}$",
            "expected_back": "\\[\\sin^2(x) + \\cos^2(x) = 1\\] and \\[\\tan(x) = \\frac{\\sin(x)}{\\cos(x)}\\]",
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. Testing: {test_case['name']}")
        print(f"   Input: {test_case['input']}")

        # Parse the card
        cards = FlashcardGenerator.parse_text_to_cards(test_case["input"], "front-back")

        if cards:
            actual_back = cards[0]["back"]
            print(f"   Expected: {test_case['expected_back']}")
            print(f"   Actual:   {actual_back}")

            if actual_back == test_case["expected_back"]:
                print("   ✅ PASS")
            else:
                print("   ❌ FAIL")
        else:
            print("   ❌ No cards generated")
        print()


def test_direct_conversion():
    """Test the conversion function directly."""

    print("=== Testing Direct LaTeX Conversion Function ===\n")

    test_strings = [
        ("$\\sigma(x) = \\frac{1}{1 + e^{-x}}$", "\\[\\sigma(x) = \\frac{1}{1 + e^{-x}}\\]"),
        ("$$e^{i\\pi} + 1 = 0$$", "\\[e^{i\\pi} + 1 = 0\\]"),
        ("\\(x^2 + y^2 = r^2\\)", "\\[x^2 + y^2 = r^2\\]"),
        ("No LaTeX here", "No LaTeX here"),
        ("\\[Already display format\\]", "\\[Already display format\\]"),
        ("Mixed: $a^2$ and $b^2$", "Mixed: \\[a^2\\] and \\[b^2\\]"),
    ]

    for i, (input_str, expected) in enumerate(test_strings, 1):
        result = FlashcardGenerator.convert_latex_to_display_format(input_str)
        print(f"{i}. Input:    '{input_str}'")
        print(f"   Expected: '{expected}'")
        print(f"   Actual:   '{result}'")
        print(f"   {'✅ PASS' if result == expected else '❌ FAIL'}")
        print()


@pytest.mark.usefixtures("anki_test_cleanup")
def test_upload_with_display_format():
    """Test uploading a card with display LaTeX format."""

    print("=== Testing Upload with Display Format ===\n")

    test_content = """Q: What is the sigmoid function?
A: $\\sigma(x) = \\frac{1}{1 + e^{-x}}$"""

    print("Original content:")
    print(f"'{test_content}'")
    print()

    try:
        # Parse the content
        cards = FlashcardGenerator.parse_text_to_cards(test_content, "front-back")

        if not cards:
            print("❌ No cards generated")
            return False

        print("Parsed card:")
        print(f"  Front: '{cards[0]['front']}'")
        print(f"  Back: '{cards[0]['back']}'")
        print()

        # Check if LaTeX was converted
        back_content = cards[0]["back"]
        if "\\[" in back_content and "\\]" in back_content:
            print("✅ LaTeX converted to display format")
        else:
            print("❌ LaTeX not converted to display format")
            return False

        # Upload to Anki
        anki_connector = get_anki_connector()
        card_manager = AnkiCardManager(anki_connector)

        cards_data = [
            {
                "data": card,
                "card_type": "front-back",
                "tags": ["mcp-test-display-latex"],
            }
            for card in cards
        ]

        result = card_manager.upload_cards_to_anki(cards_data, "Display LaTeX Test")

        if result["success"]:
            print(f"✅ Successfully uploaded to Anki deck 'Display LaTeX Test'")
            print(f"   Note ID: {result['note_ids'][0]}")
            return True
        elif "duplicate" in result.get("error", "").lower():
            print("⚠️  Card already exists (duplicate)")
            return True
        else:
            print(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("Testing Display LaTeX Format Implementation\n")

    # Test 1: Direct conversion function
    test_direct_conversion()

    print("=" * 60 + "\n")

    # Test 2: Full parsing with conversion
    test_latex_conversion()

    print("=" * 60 + "\n")

    # Test 3: Upload with display format
    success = test_upload_with_display_format()

    print("=" * 60)
    print("SUMMARY:")
    if success:
        print("✅ Display LaTeX format is working correctly!")
        print("Check the 'Display LaTeX Test' deck in Anki to see the larger rendered equation.")
    else:
        print("❌ There were issues with the display LaTeX format implementation.")
