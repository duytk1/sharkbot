"""
Auto Clicker Script
Automatically presses keys/buttons when a trigger key/button is pressed.
Press CTRL+C to exit the script.
"""

import pyautogui
import mouse
import time
import sys

# Configuration - customize these as needed
TRIGGER_BUTTON = 'right'  # 'right', 'left', or 'middle'
AUTO_PRESS_KEY = 'r'  # Automatically press 'e' key
AUTO_LEFT_CLICK = True  # Also perform left click
DELAY_BETWEEN_ACTIONS = 0.05  # Delay in seconds between actions

# Flag to stop the script
running = True

# Prevent pyautogui fail-safe
pyautogui.FAILSAFE = True


def on_right_click():
    """Called when right mouse button is clicked"""
    x, y = pyautogui.position()
    print(f"Right click detected at ({x}, {y})")
    
    # Small delay to prevent interference
    time.sleep(0.01)
    
    # Perform automated actions
    if AUTO_PRESS_KEY:
        pyautogui.press(AUTO_PRESS_KEY)
        print(f"  -> Pressed '{AUTO_PRESS_KEY}'")
        time.sleep(DELAY_BETWEEN_ACTIONS)
    
    if AUTO_LEFT_CLICK:
        pyautogui.click()
        print(f"  -> Left clicked")


def on_left_click():
    """Called when left mouse button is clicked"""
    x, y = pyautogui.position()
    print(f"Left click detected at ({x}, {y})")
    
    time.sleep(0.01)
    
    if AUTO_PRESS_KEY:
        pyautogui.press(AUTO_PRESS_KEY)
        print(f"  -> Pressed '{AUTO_PRESS_KEY}'")


def on_middle_click():
    """Called when middle mouse button is clicked"""
    x, y = pyautogui.position()
    print(f"Middle click detected at ({x}, {y})")
    
    time.sleep(0.01)
    
    if AUTO_PRESS_KEY:
        pyautogui.press(AUTO_PRESS_KEY)
        print(f"  -> Pressed '{AUTO_PRESS_KEY}'")
    
    if AUTO_LEFT_CLICK:
        pyautogui.click()
        print(f"  -> Left clicked")


def main():
    global running
    
    print("=" * 60)
    print("Auto Clicker Script Running")
    print("=" * 60)
    print(f"Trigger: {TRIGGER_BUTTON.capitalize()} Click")
    actions = []
    if AUTO_PRESS_KEY:
        actions.append(f"Press '{AUTO_PRESS_KEY}'")
    if AUTO_LEFT_CLICK:
        actions.append("Left Click")
    print(f"Actions: {' + '.join(actions)}")
    print(f"Press CTRL+C to exit")
    print("=" * 60)
    print()
    
    # Register the appropriate mouse button hook
    if TRIGGER_BUTTON == 'right':
        mouse.on_right_click(on_right_click)
    elif TRIGGER_BUTTON == 'left':
        mouse.on_click(on_left_click)
    elif TRIGGER_BUTTON == 'middle':
        mouse.on_middle_click(on_middle_click)
    else:
        print(f"Error: Unknown trigger button '{TRIGGER_BUTTON}'")
        return
    
    try:
        print("Waiting for mouse clicks...\n")
        # Keep the script running
        while running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nCTRL+C detected. Exiting...")
        running = False
    finally:
        # Clean up
        mouse.unhook_all()
        print("Script stopped.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        mouse.unhook_all()
        sys.exit(1)
