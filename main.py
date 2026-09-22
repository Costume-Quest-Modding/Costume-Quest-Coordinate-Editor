import random
import pymem
from pymem import process
import tkinter as tk

# Game process
pm = None
module_base = None
base_address = None

# Base offset for coordinates
BASE_OFFSET = 0x6903D4


def connect_to_game():
    """Try to connect to Cq.exe."""
    global pm, module_base, base_address

    try:
        # Try to open the game process
        pm = pymem.Pymem("Cq.exe")

        # Get the base address of Cq.exe
        module = process.module_from_name(pm.process_handle, "Cq.exe")
        module_base = module.lpBaseOfDll

        # Calculate the coordinate base address
        base_address = module_base + BASE_OFFSET

        location_var.set("Connected to Cq.exe")

        # Enable controls
        randomize_button.config(state=tk.NORMAL)
        apply_button.config(state=tk.NORMAL)
        refresh_button.config(state=tk.NORMAL)

        return True

    except Exception:
        pm = None
        module_base = None
        base_address = None

        location_var.set("Cq.exe not found - start the game and click Retry")

        # Disable controls
        randomize_button.config(state=tk.DISABLED)
        apply_button.config(state=tk.DISABLED)
        refresh_button.config(state=tk.DISABLED)

        return False

# List of offsets to navigate to the player position
offsets = [0xA18, 0x2C, 0x1CC, 0xB8, 0x40]

# Final offsets for X, Y, Z position
position_offset_x = 0x0
position_offset_y = 0x4
position_offset_z = 0x8

def follow_pointer_chain(base, offsets):
    """Follows a pointer chain to get to the final memory address (last offset is added directly)."""
    address = pm.read_int(base)
    for offset in offsets[:-1]:  # all except last
        if address == 0:
            raise Exception("Invalid pointer during chain walk")
        address = pm.read_int(address + offset)
    
    if address == 0:
        raise Exception("Invalid pointer at final step")
    
    # At the final step, don't read again! Just add last offset
    final_offset = offsets[-1]
    address = address + final_offset
    
    return address

def randomize_coordinates():
    """Randomizes the X, Y, and Z coordinates within a set range."""
    x = random.uniform(-5000, 5000)  
    y = random.uniform(-5000, 5000)  
    z = random.uniform(0, 100)      
    return x, y, z

def apply_randomized_coordinates():
    """Randomize coordinates and write to memory after loading save file."""
    position_address = follow_pointer_chain(base_address, offsets)
    x, y, z = randomize_coordinates()

    pm.write_float(position_address + position_offset_x, x)
    pm.write_float(position_address + position_offset_y, y)
    pm.write_float(position_address + position_offset_z, z)

    refresh_location()

def move_player(dx=0, dy=0, dz=0):
    """Move player by a delta offset in memory (dx, dy, dz)."""
    position_address = follow_pointer_chain(base_address, offsets)

    x = pm.read_float(position_address + position_offset_x)
    y = pm.read_float(position_address + position_offset_y)
    z = pm.read_float(position_address + position_offset_z)

    new_x = x + dx
    new_y = y + dy
    new_z = z + dz

    pm.write_float(position_address + position_offset_x, new_x)
    pm.write_float(position_address + position_offset_y, new_y)
    pm.write_float(position_address + position_offset_z, new_z)

    refresh_location()

def apply_manual_coordinates():
    """Apply coordinates typed in manually to memory."""
    try:
        position_address = follow_pointer_chain(base_address, offsets)
        x = float(entry_x.get())
        y = float(entry_y.get())
        z = float(entry_z.get())

        pm.write_float(position_address + position_offset_x, x)
        pm.write_float(position_address + position_offset_y, y)
        pm.write_float(position_address + position_offset_z, z)

        refresh_location()
    except ValueError:
        location_var.set("Invalid number input")

def refresh_location():
    """Refreshes the displayed coordinates in the UI."""

    if pm is None or base_address is None:
        location_var.set("Cq.exe not connected")
        return

    try:
        position_address = follow_pointer_chain(base_address, offsets)

        x = pm.read_float(position_address + position_offset_x)
        y = pm.read_float(position_address + position_offset_y)
        z = pm.read_float(position_address + position_offset_z)

        location_var.set(
            f"Current Location: {x:.2f}, {y:.2f}, {z:.2f}"
        )

        entry_x.delete(0, tk.END)
        entry_y.delete(0, tk.END)
        entry_z.delete(0, tk.END)

        entry_x.insert(0, f"{x:.2f}")
        entry_y.insert(0, f"{y:.2f}")
        entry_z.insert(0, f"{z:.2f}")

    except Exception as e:
        location_var.set(f"Error: {e}")

# GUI Setup
root = tk.Tk()
root.title("Mall Player Coordinate Editor")
root.geometry("400x400")

location_var = tk.StringVar()
location_label = tk.Label(root, textvariable=location_var)
location_label.pack(pady=10)

frame = tk.Frame(root)
frame.pack(pady=5)

# X
tk.Label(frame, text="X:").grid(row=0, column=0, padx=5)
entry_x = tk.Entry(frame, width=10)
entry_x.grid(row=0, column=1, padx=5)

# Y
tk.Label(frame, text="Y:").grid(row=1, column=0, padx=5)
entry_y = tk.Entry(frame, width=10)
entry_y.grid(row=1, column=1, padx=5)

# Z
tk.Label(frame, text="Z:").grid(row=2, column=0, padx=5)
entry_z = tk.Entry(frame, width=10)
entry_z.grid(row=2, column=1, padx=5)

# Buttons
randomize_button = tk.Button(root, text="Randomize Coordinates", command=apply_randomized_coordinates)
randomize_button.pack(pady=5)

apply_button = tk.Button(root, text="Apply Coordinates", command=apply_manual_coordinates)
apply_button.pack(pady=5)

refresh_button = tk.Button(root, text="Refresh", command=refresh_location)
refresh_button.pack(pady=5)

retry_button = tk.Button(root, text="Retry Connection",command=connect_to_game)
retry_button.pack(pady=5)

# Movement controls
controls_frame = tk.Frame(root)
controls_frame.pack(pady=10)

#Up
tk.Button(controls_frame, text="^ (1)", command=lambda: move_player(0, +1, 0)).grid(row=1, column=2)
tk.Button(controls_frame, text="^ (5)", command=lambda: move_player(0, +5, 0)).grid(row=1, column=3)
tk.Button(controls_frame, text="^ (10)", command=lambda: move_player(0, +10, 0)).grid(row=1, column=4)

#Left
tk.Button(controls_frame, text="<- (1)", command=lambda: move_player(-1, 0, 0)).grid(row=2, column=2)
tk.Button(controls_frame, text="<- (5)", command=lambda: move_player(-5, 0, 0)).grid(row=2, column=1)
tk.Button(controls_frame, text="<- (10)", command=lambda: move_player(-10, 0, 0)).grid(row=2, column=0)

#Right
tk.Button(controls_frame, text="-> (1)", command=lambda: move_player(+1, 0, 0)).grid(row=2, column=4)
tk.Button(controls_frame, text="-> (5)", command=lambda: move_player(+5, 0, 0)).grid(row=2, column=5)
tk.Button(controls_frame, text="-> (10)", command=lambda: move_player(+10, 0, 0)).grid(row=2, column=6)

#Down
tk.Button(controls_frame, text="\/ (1)", command=lambda: move_player(0, -1, 0)).grid(row=4, column=2)
tk.Button(controls_frame, text="\/ (5)", command=lambda: move_player(0, -5, 0)).grid(row=4, column=3)
tk.Button(controls_frame, text="\/ (10)", command=lambda: move_player(0, -10, 0)).grid(row=4, column=4)

connect_to_game()
root.mainloop()