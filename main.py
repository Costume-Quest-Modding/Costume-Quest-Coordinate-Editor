import ctypes
from ctypes import wintypes
import pymem
from pymem import process
import tkinter as tk

# Game process
pm = None
module_base = None
base_address = None
game_ended = False

# Base offset for coordinates
BASE_OFFSET = 0x6903D4

def is_game_running():
    """Check if the currently connected Cq.exe process is still running."""

    if pm is None:
        return False

    try:
        exit_code = wintypes.DWORD()

        result = ctypes.windll.kernel32.GetExitCodeProcess(
            pm.process_handle,
            ctypes.byref(exit_code)
        )

        # GetExitCodeProcess returns 0 if the check itself failed.
        if result == 0:
            return False

        # 259 means the process is still running.
        return exit_code.value == 259

    except Exception:
        return False

def connect_to_game():
    """Try to connect to Cq.exe."""
    global pm, module_base, base_address, game_ended

    try:
        # Try to open the game process
        pm = pymem.Pymem("Cq.exe")

        # Get the base address of Cq.exe
        module = process.module_from_name(
            pm.process_handle,
            "Cq.exe"
        )

        module_base = module.lpBaseOfDll

        # Calculate the coordinate base address
        base_address = module_base + BASE_OFFSET

        status_var.set("Connected - Found Cq.exe")
        game_ended = False

        # Enable controls
        apply_button.config(state=tk.NORMAL)

        for button in movement_buttons:
            button.config(state=tk.NORMAL)

        return True

    except Exception:
        pm = None
        module_base = None
        base_address = None

        if not game_ended:
            status_var.set(
                "Not Connected - Cq.exe not found"
                "\n\nStart the Game and click Retry"
            )

        # Disable controls
        apply_button.config(state=tk.DISABLED)

        for button in movement_buttons:
            button.config(state=tk.DISABLED)

        return False


# List of offsets to navigate to the player position
offsets = [0xA18, 0x2C, 0x1CC, 0xB8, 0x40]

# Final offsets for X, Y, Z position
position_offset_x = 0x0
position_offset_y = 0x4
position_offset_z = 0x8


def follow_pointer_chain(base, offsets):
    """Follow the pointer chain to the player position."""

    if pm is None:
        raise Exception("Not connected to Cq.exe")

    if base is None:
        raise Exception("Invalid base address")

    address = pm.read_int(base)

    for offset in offsets[:-1]:
        if address == 0:
            raise Exception("Invalid pointer during chain walk")

        address = pm.read_int(address + offset)

    if address == 0:
        raise Exception("Invalid pointer at final step")

    # At the final step, don't read again.
    return address + offsets[-1]


def move_player(dx=0, dy=0, dz=0):
    """Move player by a delta offset in memory."""

    try:
        position_address = follow_pointer_chain(
            base_address,
            offsets
        )

        x = pm.read_float(
            position_address + position_offset_x
        )

        y = pm.read_float(
            position_address + position_offset_y
        )

        z = pm.read_float(
            position_address + position_offset_z
        )

        new_x = x + dx
        new_y = y + dy
        new_z = z + dz

        pm.write_float(
            position_address + position_offset_x,
            new_x
        )

        pm.write_float(
            position_address + position_offset_y,
            new_y
        )

        pm.write_float(
            position_address + position_offset_z,
            new_z
        )

    except Exception:
        status_var.set("Connection lost")


def apply_manual_coordinates():
    """Apply coordinates typed in manually to memory."""

    try:
        position_address = follow_pointer_chain(
            base_address,
            offsets
        )

        x = float(entry_x.get())
        y = float(entry_y.get())
        z = float(entry_z.get())

        pm.write_float(
            position_address + position_offset_x,
            x
        )

        pm.write_float(
            position_address + position_offset_y,
            y
        )

        pm.write_float(
            position_address + position_offset_z,
            z
        )

    except ValueError:
        status_var.set("Invalid number input")

    except Exception:
        status_var.set("Connection lost")


def update_live_location():
    """Continuously checks for Cq.exe and player coordinates."""

    global pm, module_base, base_address, game_ended

    # -------------------------------------------------
    # Step 1: Check if we are connected to Cq.exe
    # -------------------------------------------------

    if pm is None or base_address is None:

        # If the game just ended, keep the
        # "Game process ended" message visible.
        if game_ended:
            if connect_to_game():
                live_location_var.set("Waiting for coordinates...")
                root.after(100, update_live_location)
                return

            root.after(1000, update_live_location)
            return

        # Cq.exe is not currently connected.
        # Try to find it.
        if not connect_to_game():
            live_location_var.set("Waiting for game...")

            root.after(100, update_live_location)
            return

    # -------------------------------------------------
    # Step 2: Cq.exe is connected.
    # Check if the game is still running.
    # -------------------------------------------------

    if not is_game_running():
        pm = None
        module_base = None
        base_address = None
        game_ended = True

        status_var.set(
            "Game process ended"
            "\n\nStart the Game and click Retry"
        )

        live_location_var.set("Waiting for game...")

        # Disable controls
        apply_button.config(state=tk.DISABLED)

        for button in movement_buttons:
            button.config(state=tk.DISABLED)

        root.after(100, update_live_location)
        return

    # -------------------------------------------------
    # Step 3: Cq.exe is connected.
    # Constantly check for the player coordinates.
    # -------------------------------------------------

    try:
        position_address = follow_pointer_chain(
            base_address,
            offsets
        )

        x = pm.read_float(
            position_address + position_offset_x
        )

        y = pm.read_float(
            position_address + position_offset_y
        )

        z = pm.read_float(
            position_address + position_offset_z
        )

        # Coordinates were successfully found.
        live_location_var.set(
            f"X: {x:.2f}    Y: {y:.2f}    Z: {z:.2f}"
        )

    except Exception:
        # Cq.exe is still connected, but the player
        # coordinates are not currently available.

        live_location_var.set(
            "Waiting for coordinates..."
        )

    # Run this function again in 100 milliseconds
    root.after(100, update_live_location)

# GUI Setup
root = tk.Tk()
root.title("Mall Player Coordinate Editor")
root.geometry("400x400")


# Status
status_var = tk.StringVar()
status_var.set("Not connected")

status_label = tk.Label(
    root,
    textvariable=status_var
)

status_label.pack(pady=5)


# Retry Connection
retry_button = tk.Button(
    root,
    text="Retry Connection",
    command=connect_to_game
)

retry_button.pack(pady=5)


# Live Location
live_location_var = tk.StringVar()
live_location_var.set("Waiting for coordinates...")

live_location_label = tk.Label(
    root,
    textvariable=live_location_var
)

live_location_label.pack(pady=5)


# Coordinate Entry
frame = tk.Frame(root)
frame.pack(pady=5)


# X
tk.Label(
    frame,
    text="X:"
).grid(row=0, column=0, padx=5)

entry_x = tk.Entry(
    frame,
    width=10
)

entry_x.grid(row=0, column=1, padx=5)


# Y
tk.Label(
    frame,
    text="Y:"
).grid(row=1, column=0, padx=5)

entry_y = tk.Entry(
    frame,
    width=10
)

entry_y.grid(row=1, column=1, padx=5)


# Z
tk.Label(
    frame,
    text="Z:"
).grid(row=2, column=0, padx=5)

entry_z = tk.Entry(
    frame,
    width=10
)

entry_z.grid(row=2, column=1, padx=5)


# Apply Coordinates
apply_button = tk.Button(
    root,
    text="Apply Coordinates",
    command=apply_manual_coordinates,
    state=tk.DISABLED
)

apply_button.pack(pady=5)


# Movement controls
controls_frame = tk.Frame(root)
controls_frame.pack(pady=10)

# Store movement buttons so they can all be
# enabled/disabled when the connection changes.
movement_buttons = []


# Up
button = tk.Button(
    controls_frame,
    text="↑ (1)",
    command=lambda: move_player(0, +1, 0)
)
button.grid(row=1, column=2)
movement_buttons.append(button)


button = tk.Button(
    controls_frame,
    text="↑ (5)",
    command=lambda: move_player(0, +5, 0)
)
button.grid(row=1, column=3)
movement_buttons.append(button)


button = tk.Button(
    controls_frame,
    text="↑ (10)",
    command=lambda: move_player(0, +10, 0)
)
button.grid(row=1, column=4)
movement_buttons.append(button)


# Left
button = tk.Button(
    controls_frame,
    text="← (1)",
    command=lambda: move_player(-1, 0, 0)
)
button.grid(row=2, column=2)
movement_buttons.append(button)


button = tk.Button(
    controls_frame,
    text="← (5)",
    command=lambda: move_player(-5, 0, 0)
)
button.grid(row=2, column=1)
movement_buttons.append(button)


button = tk.Button(
    controls_frame,
    text="← (10)",
    command=lambda: move_player(-10, 0, 0)
)
button.grid(row=2, column=0)
movement_buttons.append(button)


# Right
button = tk.Button(
    controls_frame,
    text="→ (1)",
    command=lambda: move_player(+1, 0, 0)
)
button.grid(row=2, column=4)
movement_buttons.append(button)


button = tk.Button(
    controls_frame,
    text="→ (5)",
    command=lambda: move_player(+5, 0, 0)
)
button.grid(row=2, column=5)
movement_buttons.append(button)


button = tk.Button(
    controls_frame,
    text="→ (10)",
    command=lambda: move_player(+10, 0, 0)
)
button.grid(row=2, column=6)
movement_buttons.append(button)


# Down
button = tk.Button(
    controls_frame,
    text="↓ (1)",
    command=lambda: move_player(0, -1, 0)
)
button.grid(row=4, column=2)
movement_buttons.append(button)


button = tk.Button(
    controls_frame,
    text="↓ (5)",
    command=lambda: move_player(0, -5, 0)
)
button.grid(row=4, column=3)
movement_buttons.append(button)


button = tk.Button(
    controls_frame,
    text="↓ (10)",
    command=lambda: move_player(0, -10, 0)
)
button.grid(row=4, column=4)
movement_buttons.append(button)


# Try to connect when the program starts
connect_to_game()


# Start live coordinate updates
update_live_location()

# Start Tkinter
root.mainloop()