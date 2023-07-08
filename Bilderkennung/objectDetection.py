# Dieses Program enthält die Bilderkennung für die
# automatische Greifsoftware.
#
# Autor: Maximilian Schnell

############################################################
# Bibliotheken                                             #
############################################################

# OpenCV
import cv2 as cv
# Numpy
import numpy as np
# Mathematik
import math
# Multithreading
import threading
import queue
# Modul-Status-Enum
from utils import Status


############################################################
# Debug-Einstellungen                                      #
############################################################

# Beispielbild statt Kamera verwenden?
DEBUG_EXAMPLE_PICTURE = False
# Bearbeitete Bilder abspechern?
DEBUG_SAVE_PICTURES = False


############################################################
# Bilderkennung                                            #
############################################################

class ObjectDetection:
    
    def __init__(self, camera_settings, camera_intrinsics, cv_parameters, object_parameters):
        
        # Kameramatrix und Settings abspeichern
        self._camera_settings = camera_settings
        self._camera_matrix, distortion_matrix = self._intrinsics_settings_to_matricies(camera_intrinsics)
        self._object_parameters = object_parameters
        
        # Variablen initialisieren
        self._img_raw = cv.imread('Bilder/Testbild.png')
        self._img_blur = cv.imread('Bilder/Testbild.png')
        self._img_binary = cv.imread('Bilder/Testbild.png')
        self._img_overlay = cv.imread('Bilder/Testbild.png')
        self._found_objects = []
        
        # Bildauslese- und Bildbearbeitungs-Thread erstellen und starten
        self._image_thread = ImageCaptureAndProcessingThread(camera_settings, self._camera_matrix, distortion_matrix, cv_parameters)
        
        self._image_thread.start()
    
    def update(self):
        # Schauen, ob ein neues Ergebnis vorhanden ist
        available, result = self._image_thread.get_result()
        
        # Falls nicht, kann abgebrochen werden
        if not available:
            return False
        
        # Ergebnis aufspalten
        (img_raw, img_blur, img_binary, img_overlay), found_objects = result
        
        # Bilder abspeichern
        self._img_raw = img_raw
        self._img_blur = img_blur
        self._img_binary = img_binary
        self._img_overlay = img_overlay
        
        if DEBUG_SAVE_PICTURES:
            cv.imwrite('Bilder/Prozessbild_raw.png', img_raw)
            cv.imwrite('Bilder/Prozessbild_blur.png', img_blur)
            cv.imwrite('Bilder/Prozessbild_binary.png', img_binary)
            cv.imwrite('Bilder/Prozessbild_overlay.png', img_overlay)
        
        # Gefundene Objekte abspeichern
        self._found_objects = found_objects
        
        return True
    
    def get_images(self):
        return self._img_raw, self._img_blur, self._img_binary, self._img_overlay
    
    def get_status(self):
        return self._image_thread.get_status()
    
    def set_cv_parameters(self, parameters):
        self._image_thread.set_cv_parameters(parameters)
    
    def get_object_at_uv(self, u_rel, v_rel):
        # Alle gefundenen Objekte durchsuchen
        for obj in self._found_objects:
            # u und v (0 bis 1) auf die Kameraauflösung anpassen
            u = u_rel * self._camera_settings['width']
            v = v_rel * self._camera_settings['height']
            # Wurde das Objekt mit der Maus getroffen?
            hit = self._check_hit_box(obj, u, v)
            if hit:
                return True, obj
        
        # => Nichts getroffen
        return False, None
    
    def get_grab_data(self, obj, extrinsics):
        # Extrinsics verarbeiten
        t_Wo_K__Wo = np.array(extrinsics[0:3])
        cam_gamma = extrinsics[3]
        c = math.cos(math.radians(cam_gamma))
        s = math.sin(math.radians(cam_gamma))
        R_K_Wo = np.array([[0, -1, 0], [-1, 0, 0], [0, 0, -1]]).dot(np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]]))
        
        # Objekt-Pose berechnen
        obj_gamma = obj['alpha'] + cam_gamma

        z_K = t_Wo_K__Wo[2] - self._object_parameters['min_depth']
        inv_cam_mat = np.linalg.inv(self._camera_matrix)
        R_Wo_K = np.transpose(R_K_Wo)
        t_K_Wo__K = R_K_Wo.dot(-t_Wo_K__Wo)
        t_Wo_K__K = -t_K_Wo__K
        r_K_obj__K = z_K * inv_cam_mat.dot(np.array([obj['u'], obj['v'], 1]))
        r_Wo_obj__K = t_Wo_K__K + r_K_obj__K
        r_Wo_obj_Wo = R_Wo_K.dot(r_Wo_obj__K)

        obj_width = obj['w'] * z_K / self._camera_matrix[0,0]
        obj_height = obj['h'] * z_K / self._camera_matrix[0,0]
        
        grab_data = {
            'x': r_Wo_obj_Wo[0],
            'y': r_Wo_obj_Wo[1],
            'z': r_Wo_obj_Wo[2],
            'gamma': obj_gamma,
            'w': obj_width,
            'h': obj_height,
        }
        
        return grab_data
    
    def _check_hit_box(self, obj, u, v):
        # Rotationsmatrix erstellen
        rot_mat = np.array([[math.cos(math.radians(-obj['alpha'])), math.sin(math.radians(-obj['alpha']))],
                            [-math.sin(math.radians(-obj['alpha'])), math.cos(math.radians(-obj['alpha']))]])
        
        # uv-Koordinaten in das Koordinatensystem des Rechteckes transformieren
        rec_coords = np.dot(rot_mat, np.array([u, v]) - np.array([obj['u'], obj['v']]))
        
        # Zurückgeben ob neue Koordinaten im Rechteck liegen
        return not (rec_coords[0] > obj['w'] / 2 or rec_coords[0] < -obj['w'] / 2 or rec_coords[1] > obj['h'] / 2 or rec_coords[1] < -obj['h'] / 2)
    
    def _intrinsics_settings_to_matricies(self, camera_intrinsics):
        camera_matrix = np.array([[camera_intrinsics['fx'], 0, camera_intrinsics['cx']],
                                  [0, camera_intrinsics['fy'], camera_intrinsics['cy']],
                                  [0, 0, 1]])
        distortion_matrix = np.array([camera_intrinsics['k1'],
                                      camera_intrinsics['k2'],
                                      camera_intrinsics['p1'],
                                      camera_intrinsics['p2']])
        return camera_matrix, distortion_matrix
    
    def __del__(self):
        # Thread anhalten
        self._image_thread.stop()

############################################################
# Bildauslese- und Bildbearbeitungs-Thread                 #
############################################################

class ImageCaptureAndProcessingThread(threading.Thread):
    
    def __init__(self, camera_settings, camera_matrix, distortion_matrix, cv_parameters):
        # Kamera- und Bilderkennungsparameter abspeichern
        self._camera_settings = camera_settings
        self._camera_matrix = camera_matrix
        self._distortion_matrix = distortion_matrix
        self._cv_parameters = cv_parameters
        
        # Variablen initialisieren
        self._status = Status.UNKNOWN
        ret, self._img_mask = cv.threshold(cv.imread('Bilder/Maske.png', cv.IMREAD_GRAYSCALE), 127, 255, cv.THRESH_BINARY)

        # Thread-Sicherheitsobjekte initialisieren
        self._stop_event = threading.Event()
        self._results_queue = queue.Queue()
        self._cv_parameters_lock = threading.Lock()
        self._status_lock = threading.Lock()

        # Thread starten
        super().__init__(daemon=True, name="ImageCaptureAndProcessingThread")
    
    def get_status(self):
        # Gleichzeitiges Zugreifen verhindern
        with self._status_lock:
            return self._status
    
    def get_result(self):
        # Neue Bilder fertig?
        available = not self._results_queue.empty()
        if available:
            # Neues Ergebnis aus der Queue ziehen
            result = self._results_queue.get()
            # Ergebnis zurückgeben
            return True, result
        else:
            # Kein neues Ergebnis
            return False, None
    
    def set_cv_parameters(self, parameters):
        # Gleichzeitiges Zugreifen verhindern
        with self._cv_parameters_lock:
            self._cv_parameters = parameters
    
    def stop(self):
        # Stop-Event setzen -> Thread wird beim nächsten Loop aufhören
        self._stop_event.set()
    
    def run(self):
        # Kameraaufnahme konfigurieren
        self._capture = cv.VideoCapture(self._camera_settings['camera_index'], cv.CAP_DSHOW)
        
        if self._capture == None or not self._capture.isOpened():
            print(f"[ERROR] Es konnte keine Verbindung zu Kamera {self._camera_settings['camera_index']} aufgebaut werden.")
            self._status = Status.ERROR
            # Thread schließen
            self._capture.release()
            return
        else:
            self._status = Status.WORKING
        
        self._capture.set(cv.CAP_PROP_FRAME_WIDTH, self._camera_settings['width'])
        self._capture.set(cv.CAP_PROP_FRAME_HEIGHT, self._camera_settings['height'])
        self._capture.set(cv.CAP_PROP_AUTOFOCUS, 0)
        self._capture.set(cv.CAP_PROP_FOCUS, 30)
        self._capture.set(cv.CAP_PROP_BUFFERSIZE, 1)

        # Bildschleife beginnen
        while not self._stop_event.is_set():
            # Rohes Kamera-/Beispielbild bekommen
            ret, img_raw = self._read_raw_image()
            if not ret:
                continue
            
            # Aktuelle Parameter kopieren (damit Lock schnell wieder frei ist)
            with self._cv_parameters_lock:
                parameters = self._cv_parameters
            
            # Bild bearbeiten
            img_undist, img_blur, img_binary = self._process_image(img_raw, parameters)
            
            # Konturen identifizieren
            contours, hierarchy = cv.findContours(img_binary, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            
            # Bei allen gefundenen Konturen:
            invalid_contours = []
            valid_contours = []
            found_objects = []
            for contour in contours:
                # Kontur überprüfen (filtern)
                if self._check_if_contour_is_valid(contour, parameters):
                    # Kontur der "guten" Liste hinzufügen
                    valid_contours.append(contour)
                    
                    # Gefundenes Objekt und seine Parameter berechnen und an Liste anheften
                    found_objects.append(self._find_object_parameters_from_contour(contour))
                else:
                    # Kontur der "schlechten" Liste hinzufügen
                    invalid_contours.append(contour)
                
            # Overlay erstellen
            img_overlay = self._create_overlay(img_undist, invalid_contours, valid_contours, found_objects)
            
            # Ergebnisse in die Queue legen
            result = ((img_raw, img_blur, img_binary, img_overlay), found_objects)
            
            if not self._results_queue.empty():
                try:
                    self._results_queue.get_nowait()
                except queue.Empty:
                    pass
            self._results_queue.put(result)
        
        # Gleichzeitiges Zugreifen verhindern
        with self._status_lock:
            self._status = Status.ERROR
        
        # Thread schließen
        self._capture.release()
        
    def _read_raw_image(self):
        # Beispielbild / Kamerabild zurückgeben
        if DEBUG_EXAMPLE_PICTURE:
            img = cv.imread('Bilder/Beispielbild.png')
            return True, img
        else:
            return self._capture.read()
    
    def _process_image(self, img_raw, parameters):
        # Bild entzerren
        img_undist = cv.undistort(img_raw, self._camera_matrix, self._distortion_matrix)
        
        # Schwarz-Weiß-Bild erstellen
        _, _, img_bw = cv.split(cv.cvtColor(img_undist, cv.COLOR_BGR2HSV))
        
        # Bild weichzeichnen, um Rauschen zu unterdrücken
        img_blur = cv.GaussianBlur(img_bw, (int(parameters['blur_kernel_size']), int(parameters['blur_kernel_size'])), 0)
        
        # Mit einem Schwellwert ein binäres Bild erstellen
        ret, img_binary = cv.threshold(img_blur, parameters['threshold_brightness'], 255, cv.THRESH_BINARY)
        
        # Die Maske anwenden, um Greifer zu verdecken
        img_binary = cv.bitwise_and(img_binary, self._img_mask)
        
        # Bilder zurückgeben
        return img_undist, img_blur, img_binary
    
    def _check_if_contour_is_valid(self, contour, parameters):
        # Flächeninhalt überprüfen
        area = cv.contourArea(contour)
        if area <= parameters['contour_min_area'] or area >= parameters['contour_max_area']:
            # Flächeninhalt zu klein oder zu groß -> aussortieren
            return False
        
        # Polygon approximieren
        epsilon = parameters['polygon_epsilon'] * cv.arcLength(contour, True)
        polygon = cv.approxPolyDP(contour, epsilon, True)
        
        # Anzahl an Eckpunkten überprüfen
        if not len(polygon) == 4:
            # Kein Rechteck -> aussortieren
            return False
        
        return True
    
    def _find_object_parameters_from_contour(self, contour):
        # Kleinstes, umschließendes Rechteck finden
        rect = cv.minAreaRect(contour)
        
        # Parameter aus Box2D-Struktur auslesen
        (center_x, center_y), (width, height), angle = rect
        
        # Mittelpunkt
        center_point = np.array([center_x, center_y])
        
        # Wenn nötig, das Rechteck drehen, dass der Winkel dem Winkel zur langen Seite entspricht
        if height > width:
            angle = angle + 90
            width, height = height, width
        angle = 180 - angle
        
        # Eckpunkte des Rechtecks finden
        box_points = np.intp(cv.boxPoints(rect))
        
        # Fläche der Kontur bestimmen
        area = cv.contourArea(contour)
        
        obj = {
            'u': center_x,
            'v': center_y,
            'alpha': angle,
            'box_points': box_points,
            'w': width,
            'h': height,
            'A': area
        }
        
        # Daten zurückgeben
        return obj
    
    def _create_overlay(self, img_undist, invalid_contours, valid_contours, found_objects):
        # Overlay-Bild erstellen
        img_overlay = img_undist.copy()
        
        # Aussortierte Konturen einzeichnen
        cv.drawContours(img_overlay, invalid_contours, -1, (0, 0, 255), 2)
        
        # Gefundene Objekte einzeichnen
        for i, object in enumerate(found_objects):
            # Bounding Box einzeichnen
            cv.polylines(img_overlay, [object['box_points']], True, (255, 0, 0), 2)
            
            # Koordinatenachsen einzeichnen
            main_axis_dir = 20 * np.array([math.cos(math.radians(object['alpha'])), -math.sin(math.radians(object['alpha']))])
            sec_axis_dir = 12 * np.array([math.sin(math.radians(object['alpha'])), math.cos(math.radians(object['alpha']))])
            cv.line(img_overlay, np.intp(np.array([object['u'], object['v']]) - main_axis_dir), np.intp(np.array([object['u'], object['v']]) + main_axis_dir), (255, 0, 0), 2)
            cv.line(img_overlay, np.intp(np.array([object['u'], object['v']]) - sec_axis_dir), np.intp(np.array([object['u'], object['v']]) + sec_axis_dir), (255, 0, 0), 2)
            
        # Bild zurückgeben
        return img_overlay