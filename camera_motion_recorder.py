# Camera Motion Detector and Recorder
# This program detects and highlights motion in real-time using the webcam and records videos when motion is detected.
# It utilizes OpenCV for webcam access, background subtraction, and motion visualization.
# Author: Arne Diehm
# Date: 03.10.2023
# Version: 1.0

import cv2
import os
import time
import tkinter as tk
from tkinter import ttk


# Einstellungen
sensitivitaet = 700  # Empfindlichkeit Bewegungserkennung
aufnahme_dauer = 30  # Dauer der Aufnahme in Sekunden nachdem Bewegung erkannt wurde
aufnahme_ordner = 'Aufnahmen'  # Ordner für Aufnahmen

# Variablen
bewegung_erkannt = False
bewegung_erkannt_realtime = False
letzte_bewegung_zeit = time.time()
aufnahme_startzeit = None
aktuelle_zeit = None
out = None
aufnahme_anzahl = 1


# Funktion zum Erstellen des Tkinter-Fensters und zur Auswahl der Kamera
def create_camera_selection_window():
    def get_available_cameras():
        num_cameras = 5  # Maximale Anzahl der zu überprüfenden Kameras
        available_cameras = [] # Liste zur Speicherung von Kamera Informationen
        camera_indices = []  # Liste zur Speicherung der Kamera-Indices

        for index in range(num_cameras):
            try:
                cap = cv2.VideoCapture(index)
                if cap is None or not cap.isOpened():
                    print('Warning: unable to open video source: ', index)
                else:
                    # Versuchen, das Kameramodell zu ermitteln
                    camera_info = cap.getBackendName()
                    if not camera_info:
                        camera_info = f"Kamera"
                    available_cameras.append(camera_info + " " + str(index))
                    camera_indices.append(index)  # Kamera-Index zur Liste hinzufügen
                cap.release()
            except cv2.error as e:
                pass  # OpenCV-spezifische Fehler können während der Suche auftreten und werden ignoriert

        return available_cameras, camera_indices

    def open_selected_camera():
        nonlocal selected_camera_index
        selected_camera_index = camera_combobox.current()
        selected_camera_index = camera_indices[camera_combobox.current()]
        root.destroy()
        return selected_camera_index

    selected_camera_index = None
    available_cameras, camera_indices = get_available_cameras()

    print(
        "\nEs wurde nach angeschlossenen Kameras gesucht. Dabei können Fehlermeldungen aufgetreten sein, die ignoriert werden können.")
    print("Verfügbare Kameras:", available_cameras)

    if not available_cameras:
        print("Keine verfügbaren Kameras gefunden.")
        return None

    if len(available_cameras) == 1:
        print("Nur eine Kamera gefunden. Diese wird automatisch ausgewählt und geöffnet.")
        selected_camera_index = camera_indices[0]
        return selected_camera_index

    # Wenn mehr als eine oder keine Kamera gefunden wurde, tkinter fenster öffnen

    root = tk.Tk()
    root.title("Kameraauswahl")

    camera_label = ttk.Label(root, text="Verfügbare Kameras:")
    camera_label.pack(pady=10)

    camera_combobox = ttk.Combobox(root, values=available_cameras)
    camera_combobox.set(available_cameras[0])
    camera_combobox.pack()

    open_button = ttk.Button(root, text="Kamera öffnen", command=open_selected_camera)
    open_button.pack(pady=10)

    root.mainloop()

    return selected_camera_index


def initialize_webcam(selected_camera_index):
    # Initialisieren der Webcam mit dem V4L2-Backend
    cap = cv2.VideoCapture(selected_camera_index, cv2.CAP_V4L2)  # (For Linux)

    # Überprüfen, ob die Webcam geöffnet wurde
    if not cap.isOpened():
        print("Fehler: Webcam konnte nicht mit V4L2 geöffnet werden. Versuche alternatives Backend.")

        # Öffnen der Webcam mit einem allgemeineren Befehl (für Windows)
        cap = cv2.VideoCapture(selected_camera_index)

        # Überprüfe erneut, ob die Webcam geöffnet wurde
        if cap.isOpened():
            print(f"Kamera {selected_camera_index} wurde erfolgreich geöffnet.")
        else:
            print(f"Fehler: Alternative Methode konnte die Webcam ({selected_camera_index}) nicht öffnen. Programm wird beendet.")
            exit(1)

    # Setze das Pixelformat auf MJPEG (falls unterstützt)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

    # Überprüfe, ob MJPEG tatsächlich gesetzt wurde
    if cap.get(cv2.CAP_PROP_FOURCC) != cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'):
        print("Warnung: MJPEG konnte nicht verwendet werden. Verwende das standardmäßige Pixelformat.")

    max_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    max_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    return cap


def find_highest_resolution(cap):

    # Liste der Auflösungen (absteigend nach Qualität)
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

        # Überprüfe, ob die eingestellte Auflösung unterstützt wird
        if (
                cap.get(cv2.CAP_PROP_FRAME_WIDTH) == width
                and cap.get(cv2.CAP_PROP_FRAME_HEIGHT) == height
        ):
            max_width = width
            max_height = height
            break

    return max_width, max_height


def initialize(max_width, max_height):
    global aufnahme_ordner
    global sensitivitaet

    if not os.path.exists(aufnahme_ordner):
        try:
            os.mkdir(aufnahme_ordner)
            print(f"Das Verzeichnis {aufnahme_ordner} wurde erstellt.")
        except OSError as e:
            print(f"Fehler beim Erstellen des Verzeichnisses {aufnahme_ordner}: {e}")
            exit(1)

    # Sensitivität auflösungsunabhängig initialisieren
    sensitivitaet = sensitivitaet * (max_width * max_height) / (1280 * 720)  # gute Parameter bei 720p ermittelt
    print(f"Auflösungsangepasste sensitivität: {sensitivitaet} Pixel")

    # Initialisieren der Hintergrundsubtraktion
    fgbg = cv2.createBackgroundSubtractorMOG2()

    return fgbg


def start_recording(video_name, max_width, max_height):
    global out

    # Liste der bevorzugten Container-Formate in der gewünschten Reihenfolge
    preferred_containers = ['MKV', 'MP4']

    # Schleife durch die bevorzugten Container-Formate
    for container_format in preferred_containers:
        if container_format == 'MKV':
            fourcc = cv2.VideoWriter_fourcc(*'X264')  # Codec für MKV
            file_extension = '.mkv'  # Dateierweiterung für MKV
        elif container_format == 'MP4':
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec für MP4
            file_extension = '.mp4'  # Dateierweiterung für MP4
        else:
            print(f"Fehler: Ungültiges Container-Format ausgewählt: {container_format}")
            continue  # Überspringen und das nächste Container-Format ausprobieren, falls ungültig

        # Videoname mit entsprechender Dateierweiterung erstellen
        video_file_name = f"{video_name}{file_extension}"

        # Versuchen, das Video mit dem ausgewählten Codec zu erstellen
        out = cv2.VideoWriter(video_file_name, fourcc, 20, (max_width, max_height))

        # Wenn das Video erfolgreich erstellt wurde, beende die Schleife
        if out.isOpened():
            print(f"Video mit dem Container: {container_format} wurde erfolgreich erstellt.")
            break
        else:
            print(f"Fehler: Konnte das Video mit dem Container: {container_format} "
                  f"und dem zugeordneten Codec nicht erstellen.")
    else:
        print("Fehler: Konnte keine Videodatei erstellen.")
        exit(1)  # Beende das Programm, wenn kein Container-Format funktioniert


def display_information(frame, contours, max_width, bewegung_erkannt_realtime, aufnahme_zeit_text,
                        aufnahme_anzahl_text):

    outframe = frame.copy()
    aktuelle_zeit = time.strftime("%d.%m.%Y %H:%M:%S")

    # Anzeige von Datum und Uhrzeit in der oberen rechten Ecke
    text_size = cv2.getTextSize(aktuelle_zeit, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    text_x = max_width - text_size[0] - 10  # X-Position für den Text
    text_y = 30  # Y-Position für den Text
    cv2.putText(frame, aktuelle_zeit, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    if bewegung_erkannt_realtime:
        cv2.putText(frame, "Bewegung erkannt", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    else:
        cv2.putText(frame, "Keine Bewegung erkannt", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(frame, aufnahme_zeit_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, aufnahme_anzahl_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Informationen im Video
    cv2.putText(outframe, aktuelle_zeit, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(outframe, aufnahme_zeit_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(outframe, aufnahme_anzahl_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Zeichnen der Konturen auf das Bild
    # cv2.drawContours(frame, contours, -1, (0, 255, 0), 1)

    frame_with_transparency = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)

    cv2.drawContours(frame_with_transparency, contours, -1, (50, 255, 0, 0), -1)

    # Konvertieren des Hintergrund-Frames in das BGRA-Format
    background_frame_with_alpha = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)

    alpha = 0.25
    frame = cv2.addWeighted(frame_with_transparency, alpha, background_frame_with_alpha, 1 - alpha, 0)#

    return frame, outframe  # Rückgabe des aktualisierten Frames mit eingezeichneten Informationen


def main():
    global bewegung_erkannt
    global aufnahme_anzahl
    global out

    selected_camera_index = create_camera_selection_window()

    if selected_camera_index is None:
        print("Keine Kamera ausgewählt.")
        exit()

    cap = initialize_webcam(selected_camera_index)

    if not cap.isOpened():
        print(f"Fehler beim Öffnen von Kamera {selected_camera_index}.")
        exit()

    max_width, max_height = find_highest_resolution(cap)

    if max_width == 0 or max_height == 0:
        print("Fehler: Keine unterstützte Auflösung gefunden.")
    else:
        print(f"Höchste unterstützte Auflösung: {max_width}x{max_height}")

    initialize(max_width, max_height)

    # Initialize Background Subtractor. Refer to README.md for information
    fgbg = cv2.createBackgroundSubtractorKNN(history=20, dist2Threshold=800.0, detectShadows=False)
    # fgbg = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=20, detectShadows=False)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # fgmask = fgbg.apply(frame)
        fgmask = fgbg.apply(frame, learningRate=0.005)  # wie schnell sich das Hintergrundmodell an Veränderungen im Bild anpasst.

        # Rauschen entfernen
        fgmask = cv2.medianBlur(fgmask, 5)

        # Kontrast erhöhen für die Konturerkennung
        alpha = 1.5
        beta = 0
        fgmask = frame_contrast = cv2.convertScaleAbs(fgmask, alpha=alpha, beta=beta)

        # Konturen finden
        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Bewegungserkennung
        for contour in contours:
            if cv2.contourArea(
                    contour) > sensitivitaet:
                if not bewegung_erkannt:
                    bewegung_erkannt = True
                    aktuelle_zeit = time.strftime("%d.%m.%y %H.%M.%S Uhr")
                    video_name = f'{aufnahme_ordner}/{aktuelle_zeit} - Aufnahme {aufnahme_anzahl}'

                    # Maximale ermittelte Auflösung für die Videoaufnahme anwenden
                    start_recording(video_name, max_width, max_height)

                    aufnahme_startzeit = time.time()
                    print(f"{time.strftime('%H:%M:%S')} Aufnahme {aufnahme_anzahl} gestartet ({video_name})")
                letzte_bewegung_zeit = time.time()
                bewegung_erkannt_realtime = True
                break
            else:
                bewegung_erkannt_realtime = False

        # Überprüfen auf Inaktivität
        if bewegung_erkannt:
            aufnahme_zeit = time.time() - letzte_bewegung_zeit
            aufnahme_zeit_in_sekunden = int(time.time() - aufnahme_startzeit)
            aufnahme_zeit_text = time.strftime("Aufnahmezeit: %M:%S", time.gmtime(aufnahme_zeit_in_sekunden))
            aufnahme_anzahl_text = f"Aufnahme: {aufnahme_anzahl}"

            if aufnahme_zeit >= aufnahme_dauer:
                print(f"Aufnahme {aufnahme_anzahl} abgeschlossen")
                out.release()

                if not out.isOpened():
                    print(f"Fehler: Konnte die Aufnahme nicht beenden: {video_name}")

                out = None
                bewegung_erkannt = False
                aufnahme_anzahl += 1

        frame, outframe = display_information(frame, contours, max_width, bewegung_erkannt_realtime,
                                              aufnahme_zeit_text, aufnahme_anzahl_text)

        if out is not None:
            out.write(outframe)

        cv2.imshow('Webcam - q druecken zum Beenden', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # ASCII-Code für "ESC"
            break

    # Aufräumen und beenden
    if out is not None:
        out.release()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
