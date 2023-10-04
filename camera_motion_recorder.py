"""
Camera Motion Detector and Recorder

This module detects and highlights motion in real-time using the webcam and records videos when motion is detected.
It utilizes OpenCV for webcam access, background subtraction, and motion visualization.

Author: Arne Diehm
Date: 03.10.2023
Version: 1.0
"""

import cv2
import os
import time
import tkinter as tk
from tkinter import ttk


# Settings
sensitivity = 700  # Motion Detection Sensitivity
recording_duration = 30  # Recording Duration in seconds after motion detection
output_folder = 'recordings'  # Folder for Recordings

# Variables
motion_detected = False
motion_detected_realtime = False
last_motion_time = None
recording_start_time = None
current_time = None
video_out = None
recording_number = 1


# Function to create the Tkinter window and select the camera
def create_camera_selection_window():
    """
    Create a tkinter window to select and open a camera.

    This function searches for available cameras and opens a tkinter window to select a camera if multiple cameras
    are detected. If only one camera is found, it will be automatically selected and opened.

    Returns:
        int or None: The selected camera index if a camera is selected, or None if no camera is available.
    """

    def get_available_cameras():
        """
        Retrieve a list of available cameras and their indices.

        This function attempts to open up to 5 camera indices to determine if a camera is available. It returns a list of
        available cameras' names along with their corresponding indices.

        Returns:
            tuple: A tuple containing two lists - available_cameras and camera_indices.
                - available_cameras (list): A list of strings containing camera names and indices.
                - camera_indices (list): A list of integers representing camera indices.
        """

        num_cameras = 5  # Maximum number of cameras to check
        available_cameras = [] # List for storing camera information
        camera_indices = []  # List for storing camera indices

        for index in range(num_cameras):
            try:
                cap = cv2.VideoCapture(index)
                if cap is None or not cap.isOpened():
                    print('Warning: unable to open video source: ', index)
                else:
                    # Trying to get the camera model
                    camera_info = cap.getBackendName()
                    if not camera_info:
                        camera_info = f"Camera"
                    available_cameras.append(camera_info + " " + str(index))
                    camera_indices.append(index)
                cap.release()
            except cv2.error as e:
                pass  # OpenCV-specific errors may occur during the search and are ignored.

        return available_cameras, camera_indices

    def open_selected_camera():
        """
        Open the camera selected in the tkinter window.

        This function retrieves the index of the camera selected by the user in the tkinter window and opens that camera.
        If successful, it sets the global variable 'selected_camera_index' to the selected camera's index and closes the
        tkinter window.

        Returns:
            int: The index of the selected camera.
        """

        nonlocal selected_camera_index
        selected_camera_index = camera_combobox.current()
        selected_camera_index = camera_indices[camera_combobox.current()]
        root.destroy()
        return selected_camera_index

    selected_camera_index = None
    available_cameras, camera_indices = get_available_cameras()

    print(
        "\nSearched for connected cameras. There may have been error messages, which can be ignored!")
    print("Available cameras: ", available_cameras)

    if not available_cameras:
        print("No available cameras found.")
        return None

    if len(available_cameras) == 1:
        print("Only one camera found. It will be automatically selected and opened.")
        selected_camera_index = camera_indices[0]
        return selected_camera_index

    # If more than one or no camera was found, open a tkinter window.

    root = tk.Tk()
    root.title("Camera selection")

    camera_label = ttk.Label(root, text="Available cameras:")
    camera_label.pack(pady=10)

    camera_combobox = ttk.Combobox(root, values=available_cameras)
    camera_combobox.set(available_cameras[0])
    camera_combobox.pack()

    open_button = ttk.Button(root, text="Open Camera", command=open_selected_camera)
    open_button.pack(pady=10)

    root.mainloop()

    return selected_camera_index


def initialize_webcam(selected_camera_index):
    """
        Initialize the webcam with the selected camera index.

        This function initializes the webcam using OpenCV's VideoCapture class. It first tries to use the V4L2-Backend
        (for Linux), and if that fails, it falls back to a more general method for opening the camera (for Windows).

        Args:
            selected_camera_index (int): The index of the selected camera.

        Returns:
            cv2.VideoCapture: The VideoCapture object for the opened camera.

        Raises:
            SystemExit: If the camera cannot be opened using any method.
        """

    # Initialize the camera with the V4L2-Backend
    cap = cv2.VideoCapture(selected_camera_index, cv2.CAP_V4L2)  # (For Linux)

    # Check if the camera has been opened
    if not cap.isOpened():
        print("Error: Unable to open the camera with V4L2. Trying an alternative backend.")

        # Open the camera using a more general commane (for windows)
        cap = cv2.VideoCapture(selected_camera_index)

        # Check again if the camera has been opened
        if cap.isOpened():
            print(f"Camera {selected_camera_index} opened successfully.")
        else:
            print(f"Error: Alternative method failed to open the camera ({selected_camera_index}). Exiting the program.")
            exit(1)

    # Set the pixel format to MJPEG (if supported)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

    # Check if MJPEG was actually set
    if cap.get(cv2.CAP_PROP_FOURCC) != cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'):
        print("Warning: MJPEG could not be used. Changing to the default pixel format.")

    max_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    max_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    return cap


def find_highest_resolution(cap):
    """
    Find the highest supported resolution for the camera.

    This function determines the highest supported resolution for the camera by testing a list of resolutions in
    descending order of quality.

    Args:
        cap (cv2.VideoCapture): The VideoCapture object for the camera.

    Returns:
        tuple: A tuple containing the maximum width and height for the supported resolution.

    Note:
        This function modifies the camera's resolution settings.
    """

    # List of resolutions (in descending order of quality)
    resolutions_to_try = [
        (1920, 1080),  # Full HD
        (1280, 720),  # HD
        (640, 480),  # VGA
        (320, 240)  # QVGA
    ]

    max_width = 0
    max_height = 0

    for width, height in resolutions_to_try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        # Check if the selected resolution is supported
        if (
                cap.get(cv2.CAP_PROP_FRAME_WIDTH) == width
                and cap.get(cv2.CAP_PROP_FRAME_HEIGHT) == height
        ):
            max_width = width
            max_height = height
            break

    return max_width, max_height


def initialize(max_width, max_height):
    """
    Initialize the motion detection parameters.

    This function initializes the sensitivity and creates the background subtractor for motion detection. Sensitivity
    is adjusted based on the camera resolution.

    Args:
        max_width (int): The maximum width of the camera's resolution.
        max_height (int): The maximum height of the camera's resolution.

    Returns:
        cv2.BackgroundSubtractorMOG2: The background subtractor object.
    """

    global output_folder
    global sensitivity

    if not os.path.exists(output_folder):
        try:
            os.mkdir(output_folder)
            print(f"The directory {output_folder} has been created.")
        except OSError as e:
            print(f"Error creating the directory {output_folder}: {e}")
            exit(1)

    # Initialize sensitivity depending on resolution
    sensitivity = sensitivity * (max_width * max_height) / (1280 * 720)  # Good parameters were determined using 720p
    print(f"Resolution-adjusted sensitivity: {sensitivity} pixels")

    # Initializing Background Subtraction
    fgbg = cv2.createBackgroundSubtractorMOG2()

    return fgbg


def start_recording(video_name, max_width, max_height):
    """
    Start video recording when motion is detected.

    This function starts video recording when motion is detected. It supports multiple container formats and codecs
    for video recording.

    Args:
        video_name (str): The base name for the video file.
        max_width (int): The maximum width of the camera's resolution.
        max_height (int): The maximum height of the camera's resolution.

    Note:
        This function uses a global variable 'video_out' to store the VideoWriter object for recording.
        It supports the MKV and MP4 container formats.

    Raises:
        SystemExit: If video recording cannot be started with any container format or codec.
    """

    global video_out

    # List of preferred container formats in desired order
    preferred_containers = ['MKV', 'MP4']

    for container_format in preferred_containers:
        if container_format == 'MKV':
            fourcc = cv2.VideoWriter_fourcc(*'X264')  # Codec for MKV
            file_extension = '.mkv'  # File extension for MKV
        elif container_format == 'MP4':
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4
            file_extension = '.mp4'  # File extension for MP4
        else:
            print(f"Error: Invalid container format selected: {container_format}")

            continue  # Skip and try the next container format if invalid

        # Create filename with file extension
        video_file_name = f"{video_name}{file_extension}"

        # Try to create the video file with the selected codec
        video_out = cv2.VideoWriter(video_file_name, fourcc, 20, (max_width, max_height))

        # Quit the loop if the video file was created successfully
        if video_out.isOpened():
            print(f"Video successfully created with container format: {container_format}")
            break
        else:
            print(f"Error: Unable to create the video with container format: {container_format} "
                  f"and the associated codec.")
    else:
        print("Error: Unable to create a video file.")
        exit(1)  # Exit the program if no container format works


def display_information(frame, contours, max_width, motion_detected_realtime, recording_time_text,
                        recording_number_text):
    """
    Display information and motion detection status on the video frame.

    This function adds date and time, motion detection status, recording duration, and total recordings to the video frame.
    It also highlights motion with contours.

    Args:
        frame (numpy.ndarray): The input video frame.
        contours (list): A list of contours representing detected motion.
        max_width (int): The maximum width of the camera's resolution.
        motion_detected_realtime (bool): Indicates whether motion is currently detected in real-time.
        recording_time_text (str): The text indicating the recording duration.
        recording_number_text (str): The text indicating the total number of recordings.

    Returns:
        tuple: A tuple containing the frame for the video file and the frame for the user interface.
    """

    outframe = frame.copy()
    current_time = time.strftime("%d.%m.%Y %H:%M:%S")

    # Date and time in the upper right corner
    text_size = cv2.getTextSize(current_time, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    text_x = max_width - text_size[0] - 10  # X-Position
    text_y = 30  # Y-Position
    cv2.putText(frame, current_time, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    if motion_detected_realtime:
        cv2.putText(frame, "Motion detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    else:
        cv2.putText(frame, "No motion detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(frame, recording_time_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, recording_number_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Informationen overlay in the Video
    cv2.putText(outframe, current_time, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(outframe, recording_time_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(outframe, recording_number_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Draw the contours on the frame
    # cv2.drawContours(frame, contours, -1, (0, 255, 0), 1)

    frame_with_transparency = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)

    cv2.drawContours(frame_with_transparency, contours, -1, (50, 255, 0, 0), -1)

    # Convert the background frame to BGRA
    background_frame_with_alpha = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)

    alpha = 0.25
    frame = cv2.addWeighted(frame_with_transparency, alpha, background_frame_with_alpha, 1 - alpha, 0)#

    return frame, outframe  # Return the frames for the video file and the user interface


def main():
    """
    The main function that controls the camera motion detection and recording process.

    This function initializes the camera, motion detection, and video recording parameters. It continuously captures frames,
    detects motion, and records videos when motion is detected. The user interface displays real-time information.

    Note:
        This function uses global variables to manage motion detection, video recording, and user interface display.
    """

    global motion_detected
    global recording_number
    global video_out

    selected_camera_index = create_camera_selection_window()

    if selected_camera_index is None:
        print("No camera selected")
        exit()

    cap = initialize_webcam(selected_camera_index)

    if not cap.isOpened():
        print(f"Error opening camera {selected_camera_index}.")
        exit()

    max_width, max_height = find_highest_resolution(cap)

    if max_width == 0 or max_height == 0:
        print("Error: No supported resolution found.")
    else:
        print(f"Highest supported resolution: {max_width}x{max_height}")

    initialize(max_width, max_height)

    # Initialize Background Subtractor. Refer to README.md for information
    fgbg = cv2.createBackgroundSubtractorKNN(history=20, dist2Threshold=800.0, detectShadows=False)
    # fgbg = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=20, detectShadows=False)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # fgmask = fgbg.apply(frame)
        fgmask = fgbg.apply(frame, learningRate=0.005)  # How quickly the background model adapts to frame changes

        # Remove noise
        fgmask = cv2.medianBlur(fgmask, 5)

        # Increase contrast for edge detection
        alpha = 1.5
        beta = 0
        fgmask = frame_contrast = cv2.convertScaleAbs(fgmask, alpha=alpha, beta=beta)

        # Find contours
        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Detect Motion
        for contour in contours:
            if cv2.contourArea(
                    contour) > sensitivity:
                if not motion_detected:
                    motion_detected = True
                    current_time = time.strftime("%d.%m.%y %H.%M.%S Uhr")
                    video_name = f'{output_folder}/{current_time} - Recording {recording_number}'

                    # Apply the maximum detected resolution for video recording
                    start_recording(video_name, max_width, max_height)

                    recording_start_time = time.time()
                    print(f"{time.strftime('%H:%M:%S')} Recording {recording_number} started ({video_name})")
                last_motion_time = time.time()
                motion_detected_realtime = True
                break
            else:
                motion_detected_realtime = False

        # Check for inactivity
        if motion_detected:
            recording_time = time.time() - last_motion_time
            recording_time_s = int(time.time() - recording_start_time)
            recording_time_text = time.strftime("Duration: %M:%S", time.gmtime(recording_time_s))
            recording_number_text = f"Total recordings: {recording_number}"

            if recording_time >= recording_duration:
                print(f"Recording {recording_number} completed")
                video_out.release()

                if not video_out.isOpened():
                    print(f"Error: Could not finish recording: {video_name}")

                video_out = None
                motion_detected = False
                recording_number += 1

        frame, outframe = display_information(frame, contours, max_width, motion_detected_realtime,
                                              recording_time_text, recording_number_text)

        if video_out is not None:
            video_out.write(outframe)

        cv2.imshow('CMDR - Press q to exit', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # ASCII-Code für "ESC"
            break

    # Clean up and quit
    if video_out is not None:
        video_out.release()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
