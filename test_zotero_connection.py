#!/usr/bin/env python3
"""
Test script to validate Zotero API credentials and connectivity
"""

import os
import sys
from pyzotero import zotero

def test_zotero_connection():
    """Test Zotero API connection with current environment variables"""
    
    # Get environment variables
    api_key = os.getenv('ZOTERO_API_KEY')
    library_id = os.getenv('ZOTERO_LIBRARY_ID')
    library_type = os.getenv('ZOTERO_LIBRARY_TYPE', 'user')
    
    print("=== Zotero Connection Test ===")
    print(f"Library Type: {library_type}")
    print(f"Library ID: {library_id}")
    print(f"API Key: {'*' * (len(api_key) - 8) + api_key[-8:] if api_key else 'NOT SET'}")
    print()
    
    # Validate environment variables
    missing_vars = []
    if not api_key:
        missing_vars.append('ZOTERO_API_KEY')
    if not library_id:
        missing_vars.append('ZOTERO_LIBRARY_ID')
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file or environment")
        return False
    
    if library_type not in ['user', 'group']:
        print(f"❌ Invalid ZOTERO_LIBRARY_TYPE: {library_type} (must be 'user' or 'group')")
        return False
    
    print("✅ Environment variables are set correctly")
    
    # Test API connection
    try:
        print("🔗 Testing API connection...")
        zot = zotero.Zotero(library_id, library_type, api_key)
        
        # Try to fetch a few items to test the connection
        items = zot.items(limit=1)
        
        print("✅ Successfully connected to Zotero API")
        print(f"📚 Found {len(items)} item(s) in your library (showing first 1)")
        
        if items:
            item = items[0]['data']
            print(f"   - Title: {item.get('title', 'No title')}")
            print(f"   - Type: {item.get('itemType', 'Unknown')}")
            print(f"   - Key: {item.get('key', 'No key')}")
        
        # Test collections
        collections = zot.collections(limit=3)
        print(f"📁 Found {len(collections)} collection(s) (showing first 3)")
        for collection in collections[:3]:
            name = collection['data'].get('name', 'Unnamed collection')
            key = collection['data'].get('key', 'No key')
            print(f"   - {name} (key: {key})")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to Zotero API: {e}")
        print(f"Error type: {type(e).__name__}")
        print()
        print("Common issues:")
        print("- Invalid API key")
        print("- Wrong library ID")
        print("- Network connectivity problems")
        print("- API key doesn't have necessary permissions")
        return False

if __name__ == "__main__":
    # Source .env file if it exists
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"📁 Loading environment variables from {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print()
    
    success = test_zotero_connection()
    sys.exit(0 if success else 1)