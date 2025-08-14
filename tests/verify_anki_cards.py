#!/usr/bin/env python3
"""
Verify that cards in Anki are using display LaTeX format.
"""

# Path handling is done by conftest.py

from mcp_server_learning.fastmcp_flashcard_server import get_anki_connector


def verify_display_latex_cards():
    """Check cards in Anki to verify they use display LaTeX format."""
    
    print("=== Verifying Display LaTeX Cards in Anki ===\n")
    
    try:
        anki_connector = get_anki_connector()
        
        # Search for our test cards
        test_queries = [
            'deck:"Display LaTeX Test"',
            'tag:display-latex-test',
            '\\['  # Cards containing display LaTeX format
        ]
        
        for query in test_queries:
            print(f"Searching for: {query}")
            
            try:
                note_ids = anki_connector.find_notes(query)
                print(f"Found {len(note_ids)} notes")
                
                if note_ids:
                    # Get details of first few notes
                    limited_ids = note_ids[:5]  # First 5 for readability
                    notes_info = anki_connector.notes_info(limited_ids)
                    
                    for i, note_info in enumerate(notes_info, 1):
                        print(f"  Note {i} (ID: {note_info['noteId']}):")
                        print(f"    Model: {note_info['modelName']}")
                        print(f"    Tags: {', '.join(note_info.get('tags', []))}")
                        
                        # Show fields and check for display LaTeX
                        fields = note_info.get("fields", {})
                        for field_name, field_value in fields.items():
                            content = field_value["value"]
                            
                            # Check for display LaTeX format
                            has_display_latex = "\\[" in content and "\\]" in content
                            has_inline_latex = "$" in content and not has_display_latex
                            
                            print(f"    {field_name}: '{content}'")
                            if has_display_latex:
                                print(f"      ✅ Contains display LaTeX format")
                            elif has_inline_latex:
                                print(f"      ⚠️  Contains inline LaTeX (should be display)")
                            
                        print()
                else:
                    print("  No notes found")
                    
            except Exception as e:
                print(f"  Error searching: {e}")
            
            print()
            
        # Summary check
        print("=== Summary Check ===")
        
        # Look for any cards that still have inline LaTeX
        inline_latex_query = '$'
        inline_notes = anki_connector.find_notes(inline_latex_query)
        
        if inline_notes:
            print(f"⚠️  Found {len(inline_notes)} cards that may still contain inline LaTeX")
            print("   This could include cards not created by this system.")
        else:
            print("✅ No cards found with inline LaTeX format")
        
        # Look for display LaTeX
        display_latex_query = '\\['
        display_notes = anki_connector.find_notes(display_latex_query)
        
        if display_notes:
            print(f"✅ Found {len(display_notes)} cards using display LaTeX format")
        else:
            print("ℹ️  No cards found with display LaTeX format")
            
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    verify_display_latex_cards()
    
    print("\n" + "="*60)
    print("INSTRUCTIONS:")
    print("1. Open Anki and navigate to 'Display LaTeX Test' deck")
    print("2. Review the sigmoid function card")
    print("3. The LaTeX should render larger than before")
    print("4. Format should be: \\[σ(x) = 1/(1 + e^(-x))\\] (display style)")
    print("5. Compare with older cards that might use $...$ (inline style)")