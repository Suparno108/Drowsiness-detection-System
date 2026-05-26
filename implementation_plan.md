# Implementation Plan: 3-Strike Drowsiness System

This plan outlines the changes needed to implement a "3-Strike" rule for drowsiness detection, where the first two strikes only trigger a warning buzzer, and the third strike triggers the gradual motor stop and phone call.

## User Review Required

> [!IMPORTANT]
> **Emergency Override:** In the current plan, once the 3rd strike happens, the car will slowly come to a stop and make the phone call. Do you want the driver to be able to "cancel" this emergency stop if they suddenly open their eyes while the car is slowing down? Or should it be an unavoidable forced stop and phone call once that 3rd strike happens? I will build it as an **unavoidable stop** unless you tell me otherwise.

> [!NOTE]
> **Resetting Strikes:** Currently, the system will count strikes forever. Once you hit 3 strikes, it triggers the emergency. To restart the counter (for example, for a new driver), you will need to restart the Python script.

## Proposed Changes

To accomplish this, we will move from our simple `D` (Drowsy) and `N` (Normal) signals, to a 3-signal system:
- `W` = Warning (Strike 1 and 2)
- `E` = Emergency (Strike 3)
- `N` = Normal (Eyes open)

---

### Python AI System

#### [MODIFY] [main.py](file:///d:/Python%20%28%20VS%20code%20%29/Drowsiness_Detection/main.py)
- **Add a `drowsy_count` variable** initialized to 0 to keep track of how many times the driver has fallen asleep.
- **Update the state machine logic**:
  - When drowsiness is detected, increment `drowsy_count` by 1.
  - If `drowsy_count` is 1 or 2, send the `'W'` (Warning) command to the ESP32.
  - If `drowsy_count` is 3, send the `'E'` (Emergency) command to the ESP32.
  - When eyes are opened, continue sending the `'N'` command.

---

### ESP32 Hardware Controller

#### [MODIFY] [esp32_controller.ino](file:///d:/Python%20%28%20VS%20code%20%29/Drowsiness_Detection/esp32_controller/esp32_controller.ino)
- **Define LED Pins:** `GREEN_LED` (GPIO18) and `RED_LED` (GPIO19).
- **Configure pins as output in `setup()`:** Start with Green LED ON and Red LED OFF.
- **Update the Serial listening logic**:
  - **If `W` is received:** Switch OFF `GREEN_LED`, switch ON `RED_LED`, and turn on the buzzer (warning alert). The motor continues running at full speed.
  - **If `N` is received:** Switch ON `GREEN_LED`, switch OFF `RED_LED`, and turn off the buzzer. Ensure the motor is running at full speed.
  - **If `E` is received:** Switch OFF `GREEN_LED`, switch ON `RED_LED`, and turn on the buzzer. Run the gradual motor slow-down loop. Once the motor hits 0, execute `makeCall()`.

## Verification Plan
1. Start the Python script and Arduino. `GREEN_LED` should be continuously ON, and `RED_LED` should be OFF.
2. Close eyes for 1st strike -> `GREEN_LED` turns OFF, `RED_LED` turns ON, Buzzer turns on. Motor stays on.
3. Open eyes -> `GREEN_LED` turns ON, `RED_LED` turns OFF, Buzzer turns off.
4. Close eyes for 2nd strike -> `GREEN_LED` turns OFF, `RED_LED` turns ON, Buzzer turns on. Motor stays on.
5. Open eyes -> `GREEN_LED` turns ON, `RED_LED` turns OFF, Buzzer turns off.
6. Close eyes for 3rd strike -> `GREEN_LED` turns OFF, `RED_LED` turns ON, Buzzer turns on, motor gradually slows to a halt over 6.5 seconds, then phone call is triggered.
