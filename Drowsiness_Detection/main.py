import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import serial
import time
from scipy.spatial import distance as dist

# Eye Aspect Ratio (EAR) threshold and consecutive frames to trigger drowsiness
EAR_THRESHOLD = 0.25
DROWSY_TIME_THRESHOLD = 3.0 # seconds

import os

# Initialize MediaPipe Face Landmarker (New Tasks API for Python 3.12 compatibility)
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, 'face_landmarker.task')
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False,
    num_faces=1
)
landmarker = vision.FaceLandmarker.create_from_options(options)

# MediaPipe face mesh landmarks for eyes
# Right Eye indices
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
# Left Eye indices
LEFT_EYE = [362, 385, 387, 263, 373, 380]

def calculate_ear(eye_points, landmarks, frame_w, frame_h):
    # Extract actual (x, y) coordinates from landmarks
    coords = []
    for point in eye_points:
        lm = landmarks[point]
        coords.append((int(lm.x * frame_w), int(lm.y * frame_h)))

    # Calculate vertical distances
    A = dist.euclidean(coords[1], coords[5])
    B = dist.euclidean(coords[2], coords[4])
    # Calculate horizontal distance
    C = dist.euclidean(coords[0], coords[3])

    # Calculate EAR
    if C == 0:
        return 0.0
    ear = (A + B) / (2.0 * C)
    return ear

import urllib.request
import json
import subprocess

def get_current_location():
    # Method 1: Try Windows native Location Services (High Accuracy Wi-Fi/GPS Triangulation)
    try:
        ps_command = (
            'Add-Type -AssemblyName System.Device; '
            '$GeoWatcher = New-Object System.Device.Location.GeoCoordinateWatcher; '
            '$GeoWatcher.Start(); '
            '$timeout = 15; '
            'while (($GeoWatcher.Status -eq "NoData" -or $GeoWatcher.Status -eq "Initializing") -and $timeout -gt 0) { '
            '  Start-Sleep -Milliseconds 200; '
            '  $timeout--; '
            '}; '
            'if ($GeoWatcher.Status -eq "Ready") { '
            '  $loc = $GeoWatcher.Position.Location; '
            '  Write-Output "$($loc.Latitude),$($loc.Longitude)"; '
            '} else { '
            '  Write-Output "FAIL"; '
            '}'
        )
        # Prevent CMD window flashing
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=5,
            startupinfo=startupinfo
        )
        output = result.stdout.strip()
        if output and output != "FAIL" and not output.startswith("Error"):
            print("Successfully obtained high-accuracy location from Windows Location Services.")
            return output
    except Exception as e:
        pass

    # Method 2: Fallback to coarse IP-based location (usually center of nearest city)
    print("Windows high-accuracy location unavailable. Falling back to IP-based location...")
    try:
        req = urllib.request.Request('https://ipinfo.io/json')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            loc = data.get('loc')
            if loc:
                return loc
    except Exception as e:
        print(f"Error fetching fallback IP location: {e}")
    return "Unknown"

# Initialize serial communication with ESP32
try:
    esp = serial.Serial('COM5', 9600)
except Exception as e:
    print(f"Failed to connect to serial port: {e}")
    esp = None

print("Fetching current GPS location...")
current_location = get_current_location()
print(f"Location obtained: {current_location}")

cap = cv2.VideoCapture(0)
closed_start = None
last_state = 'N'
drowsy_count = 0

print("Starting Camera...")

while True:
    # Read diagnostic and GSM messages from ESP32
    if esp and esp.in_waiting > 0:
        try:
            incoming = esp.readline().decode('utf-8', errors='ignore').strip()
            if incoming:
                print(f"[ESP32] {incoming}")
        except Exception as e:
            pass

    ret, frame = cap.read()
    if not ret:
        break

    # Convert BGR to RGB for MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    
    # Process the frame
    detection_result = landmarker.detect(mp_image)

    frame_h, frame_w, _ = frame.shape
    eyes_closed = False

    if len(detection_result.face_landmarks) > 0:
        for face_landmarks in detection_result.face_landmarks:
            # Calculate EAR for both eyes
            left_ear = calculate_ear(LEFT_EYE, face_landmarks, frame_w, frame_h)
            right_ear = calculate_ear(RIGHT_EYE, face_landmarks, frame_w, frame_h)

            # Average EAR
            avg_ear = (left_ear + right_ear) / 2.0

            # Display EAR on screen
            cv2.putText(frame, f"EAR: {avg_ear:.2f}", (30, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Check if EAR is below threshold
            if avg_ear < EAR_THRESHOLD:
                eyes_closed = True
                cv2.putText(frame, "EYES CLOSED", (30, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                eyes_closed = False
                cv2.putText(frame, "EYES OPEN", (30, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    if eyes_closed:
        if closed_start is None:
            closed_start = time.time()
        elif time.time() - closed_start > DROWSY_TIME_THRESHOLD:
            cv2.putText(frame, "*** DROWSY DETECTED ***", (100, 200), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            if last_state != 'D':
                drowsy_count += 1
                print(f"DROWSY DETECTED - Strike {drowsy_count}!")
                if esp:
                    if drowsy_count >= 3:
                        esp.write(f"E{current_location}\n".encode())
                    else:
                        esp.write(b"W\n")
                last_state = 'D'
    else:
        closed_start = None
        if esp and last_state != 'N':
            esp.write(b"N\n")
            last_state = 'N'

    # Display the current strike count
    cv2.putText(frame, f"Strikes: {drowsy_count}", (30, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

    cv2.imshow("Drowsiness Detection", frame)

    key = cv2.waitKey(1)
    if key == 27: # Press 'ESC' to exit
        break

cap.release()
cv2.destroyAllWindows()
