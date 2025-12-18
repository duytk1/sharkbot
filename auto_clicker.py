"""
Auto Clicker Script
Automatically presses keys/buttons when a trigger key/button is pressed.
Press CTRL+C or ESC to exit the script.
"""

import pyautogui
import keyboard
import time
import sys

# Configuration - customize these as needed
TRIGGER_KEY = 'e'  # Keyboard key that triggers the actions

# Keys to press in sequence (set to [] for none)
KEYS_TO_PRESS = ['r', 'f']  # Press T then F
AUTO_LEFT_CLICK = False  # Perform left click
DELAY_BETWEEN_ACTIONS = 0.6  # Delay in seconds between actions

# Flag to stop the script
running = True
r
# Prevent pyautogui fail-safe
pyautogui.FAILSAFE = True


def on_trigger():
    """Called when the trigger key is pressed"""
    print(f"'{TRIGGER_KEY}' key pressed")
    
    # Small delay to prevent interference
    time.sleep(DELAY_BETWEEN_ACTIONS)
    
    # Press keys in sequence
    for key in KEYS_TO_PRESS:
        pyautogui.press(key)
        print(f"  -> Pressed '{key.upper()}'")
        time.sleep(DELAY_BETWEEN_ACTIONS)
    
    if AUTO_LEFT_CLICK:
        pyautogui.click()
        print("  -> Left clicked")


def main():
    global running
    
    print("=" * 60)
    print("Auto Clicker Script Running")
    print("=" * 60)
    print(f"Trigger: '{TRIGGER_KEY}' key")
    actions = []
    if KEYS_TO_PRESS:
        key_sequence = " → ".join([k.upper() for k in KEYS_TO_PRESS])
        actions.append(f"Press {key_sequence}")
    if AUTO_LEFT_CLICK:
        actions.append("Left Click")
    print(f"Actions: {' then '.join(actions) if actions else 'None'}")
    print("Press CTRL+C to exit")
    print("=" * 60)
    print()
    
    # Register the keyboard hook for the trigger key
    keyboard.on_press_key(TRIGGER_KEY, lambda _: on_trigger())

    
    try:
        print(f"Waiting for '{TRIGGER_KEY}' key presses...\n")
        # Keep the script running
        while running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nCTRL+C detected. Exiting...")
        running = False
    finally:
        # Clean up
        keyboard.unhook_all()
        print("Script stopped.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        keyboard.unhook_all()
        sys.exit(1)
