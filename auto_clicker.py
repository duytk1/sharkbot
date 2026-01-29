"""
Auto Clicker Script
Automatically presses keys/buttons when a trigger key/button is pressed.
Press CTRL+C or ESC to exit the script.
"""

import pyautogui
import keyboard
import time
import sys
import threading
import random

# Configuration - customize these as needed
TRIGGER_KEY = 'g'  # Keyboard key that triggers the actions

# Keys to press in sequence (set to [] for none)
KEYS_TO_PRESS = ['t', 'k']  # Press R then F
AUTO_LEFT_CLICK = False  # Perform left click
DELAY_BETWEEN_ACTIONS = 0.7  # Delay in seconds between actions
DELAY_VARIANCE = 0.03  # Random variance (+/- this amount)

# Flag to stop the script
running = True
# Flag to prevent overlapping sequences
sequence_in_progress = False
# Flag to toggle the auto clicker on/off
enabled = True

# Prevent pyautogui fail-safe
pyautogui.FAILSAFE = True


def get_random_delay():
    """Returns a randomized delay time"""
    return DELAY_BETWEEN_ACTIONS + random.uniform(-DELAY_VARIANCE, DELAY_VARIANCE)


def run_sequence():
    """Runs the key sequence in a separate thread"""
    global sequence_in_progress
    
    try:
        # Small delay to prevent interference
        time.sleep(get_random_delay())
        # Press keys in sequence
        for key in KEYS_TO_PRESS:
            pyautogui.press(key)
            print(f"  -> Pressed '{key.upper()}'")
            time.sleep(get_random_delay())
        
        if AUTO_LEFT_CLICK:
            pyautogui.click()
            print("  -> Left clicked")
        
        print("  ✓ Sequence complete\n")
    finally:
        # Always reset the flag when done
        sequence_in_progress = False


def toggle_enabled():
    """Toggles the auto clicker on/off"""
    global enabled
    
    enabled = not enabled
    status = "ENABLED" if enabled else "DISABLED"
    symbol = "✓" if enabled else "⚠"
    print(f"\n{symbol} Auto clicker {status}\n")


def disable_temporarily():
    """Disables the auto clicker for 10 seconds"""
    global enabled
    
    if not enabled:
        print("Auto clicker is already disabled")
        return
    
    enabled = False
    print("\n⚠ Auto clicker DISABLED for 10 seconds\n")
    
    def re_enable():
        time.sleep(10)
        global enabled
        enabled = True
        print("✓ Auto clicker ENABLED again\n")
    
    # Run the re-enable timer in a separate thread
    thread = threading.Thread(target=re_enable, daemon=True)
    thread.start()


def on_trigger(event):
    """Called when the trigger key is pressed"""
    global sequence_in_progress, enabled
    
    # Only handle key down events
    if event.event_type != 'down':
        return
    
    # Check if auto clicker is enabled
    if not enabled:
        return
    
    # Check if a sequence is already running
    if sequence_in_progress:
        # Ignore this key press - sequence already in progress
        return
    
    # Mark that we're starting a sequence
    sequence_in_progress = True
    print(f"'{TRIGGER_KEY}' key pressed - starting sequence")
    
    # Run the sequence in a separate thread so it doesn't block keyboard input
    thread = threading.Thread(target=run_sequence, daemon=True)
    thread.start()


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
    min_delay = DELAY_BETWEEN_ACTIONS - DELAY_VARIANCE
    max_delay = DELAY_BETWEEN_ACTIONS + DELAY_VARIANCE
    print(f"Delay: {min_delay:.2f}s - {max_delay:.2f}s (randomized)")
    print("Press CTRL+C to exit")
    print("Press CTRL+T to toggle auto clicker ON/OFF")
    print("Press CTRL+R to disable auto clicker for 10 seconds")
    print("=" * 60)
    print()
    
    # Hook the trigger key (doesn't suppress, just monitors)
    keyboard.on_press_key(TRIGGER_KEY, on_trigger)
    
    # Hook Ctrl+T to toggle the auto clicker on/off
    keyboard.add_hotkey('ctrl+t', toggle_enabled)
    
    # Hook Ctrl+R to temporarily disable the auto clicker
    keyboard.add_hotkey('ctrl+r', disable_temporarily)

    try:
        print(f"Waiting for '{TRIGGER_KEY}' key presses...\n")
        print("(All other keys work normally)\n")
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
