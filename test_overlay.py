"""
Test script for the chat overlay.
This script adds test messages to the database and tests the API endpoint.
"""
import sqlite3
import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

SQL_DB_PATH = os.environ.get("SQL_CONNECT", "messages.db")
API_URL = "http://localhost:5000/api/messages"

def setup_test_database():
    """Add test messages to the database."""
    print("Setting up test database...")
    
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user TEXT NOT NULL,
                message TEXT NOT NULL,
                platform TEXT DEFAULT 'twitch'
            )
        """)
        
        # Ensure platform column exists
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN platform TEXT DEFAULT 'twitch'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Clear existing messages
        cursor.execute("DELETE FROM messages")
        
        # Add test messages
        test_messages = [
            ("viewer1", "Hello from Twitch!", "twitch"),
            ("viewer2", "This is a test message", "twitch"),
            ("youtube_user", "Hello from YouTube!", "youtube"),
            ("viewer3", "How's the stream going?", "twitch"),
            ("yt_chatter", "Great content!", "youtube"),
            ("viewer4", "Love the gameplay", "twitch"),
            ("youtube_fan", "Subscribed!", "youtube"),
            ("viewer5", "Can you explain that build?", "twitch"),
        ]
        
        for user, message, platform in test_messages:
            cursor.execute(
                "INSERT INTO messages (from_user, message, platform) VALUES (?, ?, ?)",
                (user, message, platform)
            )
        
        conn.commit()
        conn.close()
        print(f"✓ Added {len(test_messages)} test messages to database")
        return True
    except Exception as e:
        print(f"✗ Error setting up database: {e}")
        return False

def test_api_endpoint():
    """Test the API endpoint."""
    print("\nTesting API endpoint...")
    
    try:
        # Check if server is running
        response = requests.get(API_URL, timeout=5)
        
        if response.status_code == 200:
            messages = response.json()
            print(f"✓ API endpoint is working!")
            print(f"✓ Retrieved {len(messages)} messages")
            
            # Display messages
            print("\nMessages retrieved:")
            for msg in messages[:5]:  # Show first 5
                platform_icon = "🔴" if msg['platform'] == 'youtube' else "🟣"
                print(f"  {platform_icon} [{msg['platform'].upper()}] {msg['user']}: {msg['message']}")
            
            if len(messages) > 5:
                print(f"  ... and {len(messages) - 5} more")
            
            return True
        else:
            print(f"✗ API returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Is chat_overlay_server.py running?")
        print("  Start it with: python chat_overlay_server.py")
        return False
    except Exception as e:
        print(f"✗ Error testing API: {e}")
        return False

def test_html_page():
    """Test if the HTML page is accessible."""
    print("\nTesting HTML page...")
    
    try:
        response = requests.get("http://localhost:5000/", timeout=5)
        
        if response.status_code == 200:
            print("✓ HTML page is accessible")
            if "chat_overlay" in response.text.lower() or "chat-container" in response.text:
                print("✓ HTML content looks correct")
            return True
        else:
            print(f"✗ HTML page returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Is chat_overlay_server.py running?")
        return False
    except Exception as e:
        print(f"✗ Error testing HTML page: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Chat Overlay Test Script")
    print("=" * 60)
    
    # Step 1: Setup test database
    if not setup_test_database():
        print("\n⚠️  Database setup failed. Continuing with tests anyway...")
    
    # Step 2: Check if server is running
    print("\n" + "=" * 60)
    print("Step 1: Check if server is running")
    print("=" * 60)
    print("\n⚠️  Make sure chat_overlay_server.py is running in another terminal!")
    print("   Start it with: python chat_overlay_server.py")
    input("\nPress Enter when the server is running...")
    
    # Step 3: Test API endpoint
    print("\n" + "=" * 60)
    print("Step 2: Test API Endpoint")
    print("=" * 60)
    api_ok = test_api_endpoint()
    
    # Step 4: Test HTML page
    print("\n" + "=" * 60)
    print("Step 3: Test HTML Page")
    print("=" * 60)
    html_ok = test_html_page()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if api_ok and html_ok:
        print("✓ All tests passed!")
        print("\nNext steps:")
        print("1. Open http://localhost:5000 in your browser to see the overlay")
        print("2. Add http://localhost:5000 as a Browser Source in OBS")
        print("3. Messages should appear with color coding (purple=Twitch, red=YouTube)")
    else:
        print("✗ Some tests failed. Check the errors above.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

