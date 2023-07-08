# Dieses Program enthält die Darstellung (View) für die
# automatische Greifsoftware.
#
# Autor: Maximilian Schnell

############################################################
# Bibliotheken                                             #
############################################################

# Hilfsklassen
from utils import Status, RobotStatus
# Bootstrap-Erweiterung für tkinter
import ttkbootstrap as ttkb
# Pillow
from PIL import ImageTk, Image, ImageOps
# OpenCV
import cv2 as cv

############################################################
# Klassenübergreifende Funktionen                          #
############################################################

def status_to_bootstyle(status):
    match status:
        case Status.UNKNOWN:
            return 'warning'
        case Status.WORKING:
            return 'success'
        case Status.ERROR:
            return 'danger'


############################################################
# Kombinierte Widgets                                      #
############################################################

# LabeledScale:
# Ein Slider mit einer beschrifteten Umrandung und Anzeigen
# für den von-, bis- und aktuellen Wert
class LabeledScale(ttkb.LabelFrame):
    
    def __init__(self, parent, title, from_, to, increment=1, on_value_change=None):
        # LabelFrame initialisieren
        ttkb.LabelFrame.__init__(self, parent, text=title)
        
        # Benötigte Variablen abspeichern
        self._from_ = from_
        self._to = to
        self._increment = increment
        self._on_value_change_func = on_value_change
        
        # Grid (Raster) konfigurieren
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        
        # Slider erstellen
        self.scale = ttkb.Scale(self, bootstyle='primary',
                                length=400,
                                from_=from_,
                                to=to,
                                command=self._on_slider_movement)
        
        # Zahlenlabels erstellen
        self.label_from = ttkb.Label(self,
                                     text=str(from_),
                                     anchor='w',
                                     width=10)
        
        self.label_value = ttkb.Label(self, bootstyle='primary',
                                      text=str(from_),
                                      anchor='center')
        
        self.label_to = ttkb.Label(self,
                                   text=str(to),
                                   anchor='e',
                                   width=10)
        
        # Widgets im Grid plazieren
        self.scale.grid(row=0, column=0, columnspan=3, padx=5, pady=(0, 5), sticky='we')
        self.label_from.grid(row=1, column=0, padx=5, pady=0, sticky='w')
        self.label_value.grid(row=1, column=1, padx=5, pady=0, sticky='we')
        self.label_to.grid(row=1, column=2, padx=5, pady=0, sticky='e')
    
    def get_value(self):
        # Slider-Wert zurückgeben
        return self.scale.get()
    
    def set_value(self, value):
        # Wert diskretisieren
        value=self._fit_value_to_increments(value)
        
        # Wert auf Slider anwenden
        self.scale.configure(value=value)
        
        # Wert-Label aktualisieren
        self._update_value_label(value)
    
    def _on_slider_movement(self, value):
        # Wert zum nächsten Inkrementpunkt drücken und anwenden
        self.set_value(value)
        
        # Controller Bescheid geben, dass sich ein Wert geändert hat
        if not self._on_value_change_func == None:
            self._on_value_change_func()
    
    def _update_value_label(self, value):
        # Wert-Label aktualisieren
        self.label_value.configure(text=str(value))
        
    def _fit_value_to_increments(self, value):
        # Wert diskretisieren
        value = self._from_ + round((float(value) - self._from_) / self._increment) * self._increment
        
        # Wert auf Slider-Intervall begrenzen
        value = max(min(value, self._to), self._from_)
        
        # Diskretisierten und begrenzten Wert zurückgeben
        return value

# LabeledImagePanel:
# Ein Bildpanel mit einer beschrifteten Umrandung
class LabeledImagePanel(ttkb.LabelFrame):
    
    def __init__(self, parent, title):
        # LabelFrame initialisieren
        ttkb.LabelFrame.__init__(self, parent, text=title)
        
        # Bildpanel erstellen und plazieren
        self._panel = ttkb.Label(self)
        self._panel.pack(padx=5, pady=5)
    
    def set_image(self, img):
        # Bild auf panel anwenden
        self._panel.configure(image=img)
        self._panel.image = img

# LabeledEntry:
# Ein Label mit Eingabefeld daneben
class LabeledEntry(ttkb.Frame):
    
    def __init__(self, parent, name, data_type='float'):
        # LabelFrame initialisieren
        ttkb.Frame.__init__(self, parent)
        
        # Sub-Komponenten erstellen
        self._label = ttkb.Label(self, text=name + " =", width=30)
        if data_type == 'int':
            self._value = ttkb.IntVar()
        elif data_type == 'float':
            self._value = ttkb.DoubleVar()
        else:
            self._value = ttkb.StringVar()
        self._value.trace('w', self._on_value_changed)
        self._entry = ttkb.Entry(self, bootstyle='warning', width=20, textvariable=self._value)
        
        self._label.grid(row=0, column=0)
        self._entry.grid(row=0, column=1)
    
    def set_value(self, value):
        # Value in Entry-Element eintragen
        self._value.set(value)
    
    def get_value(self):
        # Wert zurückgeben
        return self._value.get()
    
    def confirm_value(self):
        # Entry-Element blau machen, da der Wert nun dem aktuellen entsprechen sollte
        self._entry.configure(bootstyle='primary')
            
    def _on_value_changed(self, a, b, c):
        # Der Wert ist neu und noch nicht angewand, somit wird das Entry-Element gelb
        self._entry.configure(bootstyle='warning')

# NamedLabelWithUnit:
# Ein Element mit dem Variablennamen, dem Wert und der Einheit
class NamedLabelWithUnit(ttkb.Frame):
    
    def __init__(self, parent, name, unit, decimal_places = 2):
        # Variablen abspeichern
        self.decimal_places = decimal_places
        
        # LabelFrame initialisieren
        ttkb.Frame.__init__(self, parent)
        
        # Spalten konfigurieren
        self.columnconfigure(1, weight=1)
        
        # Sub-Komponenten erstellen
        self._name_label = ttkb.Label(self, text=name + " =", width=15)
        self._number_label = ttkb.Label(self, text="", width=10, justify='right', anchor='e')
        self._unit_label = ttkb.Label(self, text=str(unit), width=5)
        
        # Komponenten plazieren
        self._name_label.grid(row=0, column=0)
        self._number_label.grid(row=0, column=1, padx=10, sticky='e')
        self._unit_label.grid(row=0, column=2, sticky='e')
    
    def set_value(self, value):
        # Value in Entry-Element eintragen
        self._number_label.configure(text=f"{value:.{self.decimal_places}f}")


############################################################
# Seite: "Greifsteuerung"                                  #
############################################################

class ControllerPage(ttkb.Frame):
    
    def __init__(self, parent):
        # Frame initialisieren
        ttkb.Frame.__init__(self, parent)
        
        # Callback-Funktionen als None initialisieren
        self._grab_object_at_uv_func = None
        self._return_object_at_uv_info_func = None
        
        # Variablen initialisieren
        self._enable_overlay = False
        self._show_object_info = False
        
        # Widgets erstellen
        self._status_wrapper = ttkb.Frame(self)
        self._status_label = ttkb.Label(self._status_wrapper, text="Status:", font=('Arial', 20))
        self._status_text_label = ttkb.Label(self._status_wrapper, text="Unbekannt", font=('Arial', 20), bootstyle='warning')

        self._image_panel = ttkb.Label(self)
        
        self._object_info_frame = ttkb.LabelFrame(self, text="Objekt")
        self._object_info_section1 = ttkb.Label(self._object_info_frame, text="Bild-Koordinaten", bootstyle='inverse-dark', anchor='center')
        self._object_info_section2 = ttkb.Label(self._object_info_frame, text="Werkobjekt-Koordinaten", bootstyle='inverse-dark', anchor='center')
        
        self._object_picture_named_labels = {
            'u': NamedLabelWithUnit(self._object_info_frame, "U-Koordinate", "Px"),
            'v': NamedLabelWithUnit(self._object_info_frame, "V-Koordinate", "Px"),
            'alpha': NamedLabelWithUnit(self._object_info_frame, "Winkel", "°"),
            'w': NamedLabelWithUnit(self._object_info_frame, "Breite", "Px"),
            'h': NamedLabelWithUnit(self._object_info_frame, "Höhe", "Px"),
            'A': NamedLabelWithUnit(self._object_info_frame, "Fläche", "Px^2")
        }
        self._object_grab_named_labels = {
            'x': NamedLabelWithUnit(self._object_info_frame, "X-Koordinate", "mm"),
            'y': NamedLabelWithUnit(self._object_info_frame, "Y-Koordinate", "mm"),
            'z': NamedLabelWithUnit(self._object_info_frame, "Z-Koordinate", "mm"),
            'gamma': NamedLabelWithUnit(self._object_info_frame, "Gamma", "°"),
            'w': NamedLabelWithUnit(self._object_info_frame, "Breite", "mm"),
            'h': NamedLabelWithUnit(self._object_info_frame, "Höhe", "mm"),
        }
        
        # Widgets plazieren
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)
        
        self._status_wrapper.grid(row=0, column=0, sticky='w')

        self._status_label.grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self._status_text_label.grid(row=0, column=1, padx=10, pady=10, sticky='w')
        
        self._image_panel.grid(row=1, column=0, padx=10, pady=(0,10), sticky='ws')
        
        self._object_info_frame.grid(row=1, column=1, padx=10, pady=5, sticky='nw')
        
        self._object_info_section1.pack(padx=10, pady=(10, 5), side='top', fill='x')
        self._object_picture_named_labels['u'].pack(padx=10, pady=5, fill='x')
        self._object_picture_named_labels['v'].pack(padx=10, pady=5, fill='x')
        self._object_picture_named_labels['alpha'].pack(padx=10, pady=5, fill='x')
        self._object_picture_named_labels['w'].pack(padx=10, pady=5, fill='x')
        self._object_picture_named_labels['h'].pack(padx=10, pady=5, fill='x')
        self._object_picture_named_labels['A'].pack(padx=10, pady=5, fill='x')
        self._object_info_section2.pack(padx=10, pady=(10, 5), side='top', fill='x')
        self._object_grab_named_labels['x'].pack(padx=10, pady=5, fill='x')
        self._object_grab_named_labels['y'].pack(padx=10, pady=5, fill='x')
        self._object_grab_named_labels['z'].pack(padx=10, pady=5, fill='x')
        self._object_grab_named_labels['gamma'].pack(padx=10, pady=5, fill='x')
        self._object_grab_named_labels['w'].pack(padx=10, pady=5, fill='x')
        self._object_grab_named_labels['h'].pack(padx=10, pady=(5,10), fill='x')
        
        self._object_info_frame.grid_remove()
        
        # Events anbinden
        self._image_panel.bind('<Button-1>', self._on_image_panel_pressed)
        self._image_panel.bind('<Motion>', self._on_image_panel_mouse_move)
    
    ##### Event-Funktionen #####
    
    def _on_image_panel_pressed(self, event):
        # Nichts tun, wenn das Overlay nicht an ist
        if not self._enable_overlay:
            return
        
        # Relative u,v-Koordinaten berechnen
        u_rel = event.x / float(self._image_panel.image.width())
        v_rel = event.y / float(self._image_panel.image.height())
        
        # Parameter an Controller übergeben
        if not self._grab_object_at_uv_func == None:
            self._grab_object_at_uv_func(u_rel, v_rel)
    
    def _on_image_panel_mouse_move(self, event):
        # Nichts tun, wenn das Overlay nicht an ist
        if not self._enable_overlay:
            return
        
        # Relative u,v-Koordinaten berechnen
        u_rel = event.x / float(self._image_panel.image.width())
        v_rel = event.y / float(self._image_panel.image.height())
        
        # Parameter an Controller übergeben
        if not self._return_object_at_uv_info_func == None:
            hit, object_info = self._return_object_at_uv_info_func(u_rel, v_rel)
            if hit:
                # Labels aktualisieren
                for key, element in self._object_picture_named_labels.items():
                    element.set_value(object_info['picture_info'][key])
                for key, element in self._object_grab_named_labels.items():
                    element.set_value(object_info['grab_data'][key])
                
                # Info sichtbar machen
                if not self._show_object_info:
                    self._object_info_frame.grid()
                    self._show_object_info = True
            else:
                # Info unsichtbar machen
                if self._show_object_info:
                    self._object_info_frame.grid_remove()
                    self._show_object_info = False
    
    ##### Anzeige-Aktualisierungs-Funktionen #####
    
    def update_images(self, img_raw, img_overlay):
        if self._enable_overlay:
            img_overlay = ImageTk.PhotoImage(ImageOps.contain(img_overlay, (1280, 960)))
            self._image_panel.configure(image=img_overlay)
            self._image_panel.image = img_overlay
        else:
            img_raw = ImageTk.PhotoImage(ImageOps.contain(img_raw, (1280, 960)))
            self._image_panel.configure(image=img_raw)
            self._image_panel.image = img_raw
    
    def update_status(self, objectDetection_status, rob_status):
        # Zwischen Overlay und Kamerabild wechseln
        if rob_status == RobotStatus.WAITING:
            self._enable_overlay = True
        else:
            self._enable_overlay = False
        
        # Status Text aktualisieren
        match objectDetection_status:
            case Status.WORKING:
                match rob_status:
                    case RobotStatus.NOT_CONNECTED:
                        self._status_text_label.configure(text="Roboter ist noch nicht verbunden", bootstyle='warning')
                    case RobotStatus.STARTUP:
                        self._status_text_label.configure(text="Roboter fährt zur Sicherheitsposition", bootstyle='success')
                    case RobotStatus.MOVING_CAMERA:
                        self._status_text_label.configure(text="Roboter fährt zur Kameraposition", bootstyle='success')
                    case RobotStatus.WAITING:
                        self._status_text_label.configure(text="Bitte Objekt zum Greifen auswählen", bootstyle='success')
                    case RobotStatus.GRABBING:
                        self._status_text_label.configure(text="Roboter greift das Objekt", bootstyle='success')
                    case RobotStatus.MOVING_PLACE:
                        self._status_text_label.configure(text="Roboter fährt zur Plazierposition", bootstyle='success')
                    case RobotStatus.PLACING:
                        self._status_text_label.configure(text="Roboter plaziert das Objekt", bootstyle='success')
                    case RobotStatus.ERROR:
                        self._status_text_label.configure(text="Fehler bei der Roboterkommunikation", bootstyle='danger')
            case Status.UNKNOWN:
                self._status_text_label.configure(text="Bilderkennung ist noch nicht gestartet", bootstyle='warning')
            case Status.ERROR:
                self._status_text_label.configure(text="Kamera konnte nicht gefunden werden", bootstyle='danger')
    
    ##### Callback-Zuweis-Funktionen #####
    
    def bind_grab_object_at_uv_func(self, func):
        self._grab_object_at_uv_func = func
    
    def bind_return_object_at_uv_info_func(self, func):
        self._return_object_at_uv_info_func = func


############################################################
# Seite: "Bilderkennung: Parameter einstellen"             #
############################################################

class DetectionParametersPage(ttkb.Frame):
    
    def __init__(self, parent):
        # Frame initialisieren
        ttkb.Frame.__init__(self, parent)
        
        # Callback-Funktionen als None initialisieren
        self._update_cv_parameters_func = None
        self._save_cv_parameters_func = None
        
        # Frame (links) für das Bilder-Grid erstellen
        self._left_frame = ttkb.LabelFrame(self, bootstyle='dark',text="Vorschau")
        
        # Frame (rechts) für die Einstellungs-Slider und Speicherbutton erstellen
        self._right_frame = ttkb.LabelFrame(self, bootstyle='dark', text="Parameter")
        
        self._left_frame.columnconfigure(0, weight=1)
        self._left_frame.columnconfigure(1, weight=1)
        
        # Bildpanels erstellen
        self._image_panel_raw = LabeledImagePanel(self._left_frame, title="(1) Kamerabild")
        self._image_panel_blur = LabeledImagePanel(self._left_frame, title="(2) Entzerrung und Weichzeichnen")
        self._image_panel_binary = LabeledImagePanel(self._left_frame, title="(3) Schwellwert")
        self._image_panel_overlay = LabeledImagePanel(self._left_frame, title="(4) Umrisserkennung")
        
        # Process-Labels erstellen
        self._label_process_12 = ttkb.Label(self._right_frame, text="1 -> 2", bootstyle='inverse-dark', anchor='center')
        self._label_process_23 = ttkb.Label(self._right_frame, text="2 -> 3", bootstyle='inverse-dark', anchor='center')
        self._label_process_34 = ttkb.Label(self._right_frame, text="3 -> 4", bootstyle='inverse-dark', anchor='center')
        
        # Slider erstellen
        self._slider_1 = LabeledScale(self._right_frame, title="Gauß-Filter - Kernelgröße",
                                     from_=1, to=13, increment=2,
                                     on_value_change=self._on_parameters_change)
        
        self._slider_2 = LabeledScale(self._right_frame, "Schwellwert - Helligkeit",
                                     from_=0, to=255, increment=1,
                                     on_value_change=self._on_parameters_change)
        
        self._slider_3 = LabeledScale(self._right_frame, "Kontourerkennung - Flächeninhalt (min)",
                                     from_=500, to=10000, increment=100,
                                     on_value_change=self._on_parameters_change)
        
        self._slider_4 = LabeledScale(self._right_frame, "Kontourerkennung - Flächeninhalt (max)",
                                     from_=1000, to=50000, increment=200,
                                     on_value_change=self._on_parameters_change)
        
        self._slider_5 = LabeledScale(self._right_frame, "Polygonapproximation - Genauigkeit",
                                     from_=0, to=0.1, increment=0.005,
                                     on_value_change=self._on_parameters_change)
        
        # Knopf zum Speichern der Parameter
        self._save_parameters_button = ttkb.Button(self._right_frame, text="Parameter speichern", command=self._on_save_parameters_pressed)
        
        # Widgets im linken Frame plazieren
        self._image_panel_raw.grid(row=0, column=0, padx=10, pady=5, sticky='we')
        self._image_panel_blur.grid(row=0, column=1, padx=10, pady=5, sticky='we')
        self._image_panel_binary.grid(row=1, column=0, padx=10, pady=5, sticky='we')
        self._image_panel_overlay.grid(row=1, column=1, padx=10, pady=5, sticky='we')
        
        # Widgets im rechten Frame plazieren
        self._label_process_12.pack(padx=10, pady=(10, 5), side='top', fill='x')
        self._slider_1.pack(padx=10, pady=(5, 25), side='top')
        self._label_process_23.pack(padx=10, pady=(10, 5), side='top', fill='x')
        self._slider_2.pack(padx=10, pady=(5, 25), side='top')
        self._label_process_34.pack(padx=10, pady=(10, 5), side='top', fill='x')
        self._slider_3.pack(padx=10, pady=5, side='top')
        self._slider_4.pack(padx=10, pady=5, side='top')
        self._slider_5.pack(padx=10, pady=5, side='top')
        self._save_parameters_button.pack(padx=5, pady=5, side='bottom', fill='x')
        
        # Frames (links & rechts) plazieren
        self._right_frame.pack(padx=20, pady=(10,20), side='right', fill='y')
        self._left_frame.pack(padx=20, pady=(10,20), side='left', expand=True, fill='both')
    
    ##### Callback-Zuweis-Funktionen #####
    
    def bind_update_cv_parameters_func(self, func):
        # Callback-Funktion zuweisen
        self._update_cv_parameters_func = func
    
    def bind_save_cv_parameters_func(self, func):
        # Callback-Funktion zuweisen
        self._save_cv_parameters_func = func
    
    ##### Event-Funktionen #####
    
    def _on_parameters_change(self):
        # Slider auslesen und zu Parametern zusammenfassen
        parameters = self._compile_parameters()
        
        # Neue Parameter an Controller übergeben
        if not self._update_cv_parameters_func == None:
            self._update_cv_parameters_func(parameters)
    
    def _on_save_parameters_pressed(self):
        # Slider auslesen und zu Parametern zusammenfassen
        parameters = self._compile_parameters()
        
        # Parameter an Controller zum Abspeichern übergeben
        if not self._save_cv_parameters_func == None:
            self._save_cv_parameters_func(parameters)
    
    ##### Anzeige-Aktualisierungs-Funktionen #####
    
    def update_images(self, img_raw, img_blur, img_binary, img_overlay):
        # Bilder aktualisieren
        self._image_panel_raw.set_image(ImageTk.PhotoImage(ImageOps.contain(img_raw, (605, 525))))
        self._image_panel_blur.set_image(ImageTk.PhotoImage(ImageOps.contain(img_blur, (605, 525))))
        self._image_panel_binary.set_image(ImageTk.PhotoImage(ImageOps.contain(img_binary, (605, 525))))
        self._image_panel_overlay.set_image(ImageTk.PhotoImage(ImageOps.contain(img_overlay, (605, 525))))
    
    def overwrite_parameters(self, parameters):
        # Slider auf die Werte der vorgegebenen Einstellung setzten
        self._slider_1.set_value(parameters['blur_kernel_size'])
        self._slider_2.set_value(parameters['threshold_brightness'])
        self._slider_3.set_value(parameters['contour_min_area'])
        self._slider_4.set_value(parameters['contour_max_area'])
        self._slider_5.set_value(parameters['polygon_epsilon'])
    
    ##### Sonstige Funktionen #####
    
    def _compile_parameters(self):
        # Slider auslesen und zu Parameter zusammenfassen
        parameters = {
            'blur_kernel_size': self._slider_1.get_value(),
            'threshold_brightness': self._slider_2.get_value(),
            'contour_min_area': self._slider_3.get_value(),
            'contour_max_area': self._slider_4.get_value(),
            'polygon_epsilon': self._slider_5.get_value()
        }
        # Parameter gebündelt zurückgeben
        return parameters

############################################################
# Seite: "Einstellungen"                                   #
############################################################

class SettingsPage(ttkb.Frame):
    
    def __init__(self, parent):
        # Frame initialisieren
        ttkb.Frame.__init__(self, parent)
        
        self.rowconfigure(0, weight=1)
        
        # Callback-Funktionen als None initialisieren
        self._retry_objectDetection_func = None
        self._retry_robotController_func = None
        
        ##### Kamera-Einstellungen #####
        
        # Frame
        self._camera_settings_frame = ttkb.LabelFrame(self, bootstyle='warning',text="Kamera-Einstellungen")
        
        # Unterüberschriften
        self._camera_settings_section1 = ttkb.Label(self._camera_settings_frame, text="Allgemein", bootstyle='inverse-dark', anchor='center')
        self._camera_settings_section2 = ttkb.Label(self._camera_settings_frame, text="Kamera-Matrix", bootstyle='inverse-dark', anchor='center')
        self._camera_settings_section3 = ttkb.Label(self._camera_settings_frame, text="Verzerrung", bootstyle='inverse-dark', anchor='center')
        self._camera_settings_section4 = ttkb.Label(self._camera_settings_frame, text="Greifobjekt-Parameter", bootstyle='inverse-dark', anchor='center')
        
        # Eingabefelder
        self._camera_settings_entries = {
            'camera_index': LabeledEntry(self._camera_settings_frame, "Kamera ID", data_type='int'),
            'width': LabeledEntry(self._camera_settings_frame, "Breite", data_type='int'),
            'height': LabeledEntry(self._camera_settings_frame, "Höhe", data_type='int')
        }
        self._camera_intrinsics_entries = {
            'fx': LabeledEntry(self._camera_settings_frame, "Brennweite (X)"),
            'fy': LabeledEntry(self._camera_settings_frame, "Brennweite (Y)"),
            'cx': LabeledEntry(self._camera_settings_frame, "Kamerahauptpunkt (X)"),
            'cy': LabeledEntry(self._camera_settings_frame, "Kamerahauptpunkt (Y)"),
            
            'k1': LabeledEntry(self._camera_settings_frame, "Radiale Verzerrung (k1)"),
            'k2': LabeledEntry(self._camera_settings_frame, "Radiale Verzerrung (k2)"),
            'p1': LabeledEntry(self._camera_settings_frame, "Tangentiale Verzerrung (p1)"),
            'p2': LabeledEntry(self._camera_settings_frame, "Tangentiale Verzerrung (p2)")
        }
        self._objects_parameters_entry = LabeledEntry(self._camera_settings_frame, "Geringste Dicke (Z)")
        
        # Button zum Anwenden der angegebenen Einstellungen
        self._retry_objectDetection_button = ttkb.Button(self._camera_settings_frame, text="Bilderkennung neu starten", command=self._on_retry_objectDetection_pressed)
        
        ##### Roboter-Einstellungen #####
        
        # Frame
        self._robot_settings_frame = ttkb.LabelFrame(self, bootstyle='warning',text="Roboter-Einstellungen")
        
        # Unterüberschriften
        self._robot_settings_section1 = ttkb.Label(self._robot_settings_frame, text="Server (Roboter)", bootstyle='inverse-dark', anchor='center')
        self._robot_settings_section2 = ttkb.Label(self._robot_settings_frame, text="Kamera-Startposition", bootstyle='inverse-dark', anchor='center')
        
        # Eingabefelder
        self._server_entries = {
            'ip': LabeledEntry(self._robot_settings_frame, "Server IP", data_type='str'),
            'port': LabeledEntry(self._robot_settings_frame, "Server Port", data_type='int')
        }
        self._cam_pos_entries = {
            'x': LabeledEntry(self._robot_settings_frame, "X"),
            'y': LabeledEntry(self._robot_settings_frame, "Y"),
            'z': LabeledEntry(self._robot_settings_frame, "Z"),
            'gamma': LabeledEntry(self._robot_settings_frame, "Gamma")
        }
        
        # Button zum Anwenden der angegebenen Einstellungen
        self._retry_robotController_button = ttkb.Button(self._robot_settings_frame, text="Roboterverbindung neu starten", command=self._on_retry_robotController_pressed)
        
        ##### Widgets plazieren #####
        
        # Kamera-Bereich
        self._camera_settings_frame.grid(row=0, column=0, padx=20, pady=(10,20), sticky='nse')
        
        # Kamera-Bereich: Inhalte
        self._camera_settings_section1.pack(padx=10, pady=(10, 5), side='top', fill='x')
        self._camera_settings_entries['camera_index'].pack(padx=10, pady=5)
        self._camera_settings_entries['width'].pack(padx=10, pady=5)
        self._camera_settings_entries['height'].pack(padx=10, pady=5)
        
        self._camera_settings_section2.pack(padx=10, pady=(10, 5), side='top', fill='x')
        self._camera_intrinsics_entries['fx'].pack(padx=10, pady=5)
        self._camera_intrinsics_entries['fy'].pack(padx=10, pady=5)
        self._camera_intrinsics_entries['cx'].pack(padx=10, pady=5)
        self._camera_intrinsics_entries['cy'].pack(padx=10, pady=5)
        
        self._camera_settings_section3.pack(padx=10, pady=(10, 5), side='top', fill='x')
        self._camera_intrinsics_entries['k1'].pack(padx=10, pady=5)
        self._camera_intrinsics_entries['k2'].pack(padx=10, pady=5)
        self._camera_intrinsics_entries['p1'].pack(padx=10, pady=5)
        self._camera_intrinsics_entries['p2'].pack(padx=10, pady=5)
        
        self._camera_settings_section4.pack(padx=10, pady=(10, 5), side='top', fill='x')
        self._objects_parameters_entry.pack(padx=10, pady=5)
        
        self._retry_objectDetection_button.pack(padx=10, pady=10, side='bottom', fill='x')
        
        # Roboter-Bereich
        self._robot_settings_frame.grid(row=0, column=1, padx=20, pady=(10,20), sticky='nse')
        
        # Roboter-Bereich: Inhalte
        self._robot_settings_section1.pack(padx=10, pady=(10, 5), side='top', fill='x')
        self._server_entries['ip'].pack(padx=10, pady=5)
        self._server_entries['port'].pack(padx=10, pady=5)
        
        self._robot_settings_section2.pack(padx=10, pady=(10, 5), side='top', fill='x')
        self._cam_pos_entries['x'].pack(padx=10, pady=5)
        self._cam_pos_entries['y'].pack(padx=10, pady=5)
        self._cam_pos_entries['z'].pack(padx=10, pady=5)
        self._cam_pos_entries['gamma'].pack(padx=10, pady=5)
        
        self._retry_robotController_button.pack(padx=10, pady=10, side='bottom', fill='x')
    
    ##### Callback-Zuweis-Funktionen #####
    
    def bind_retry_objectDetection_func(self, func):
        # Callback-Funktion zuweisen
        self._retry_objectDetection_func = func
    
    def bind_retry_robotController_func(self, func):
        # Callback-Funktion zuweisen
        self._retry_robotController_func = func
    
    ##### Event-Funktionen #####
    
    def _on_retry_objectDetection_pressed(self):
        # Einstellungen compilieren
        settings = {'camera_settings': {}, 'camera_intrinsics': {}, 'objects_parameters': {}}
        for key, element in self._camera_settings_entries.items():
            settings['camera_settings'][key] = element.get_value()
            element.confirm_value()
        for key, element in self._camera_intrinsics_entries.items():
            settings['camera_intrinsics'][key] = element.get_value()
            element.confirm_value()
        settings['objects_parameters']['min_depth'] = self._objects_parameters_entry.get_value()
        
        # Neue Einstellungen an Controller übergeben
        if not self._retry_objectDetection_func == None:
            self._retry_objectDetection_func(settings)
    
    def _on_retry_robotController_pressed(self):
        # Einstellungen compilieren
        settings = {'server': {}, 'initial_camera_pose': {}}
        for key, element in self._server_entries.items():
            settings['server'][key] = element.get_value()
            element.confirm_value()
        for key, element in self._cam_pos_entries.items():
            settings['initial_camera_pose'][key] = element.get_value()
            element.confirm_value()
        
        # Neue Einstellungen an Controller übergeben
        if not self._retry_robotController_func == None:
            self._retry_robotController_func(settings)
    
    ##### Anzeige-Aktualisierungs-Funktionen #####
    
    def update_objectDetection_status(self, status):
        # Kamera-Einstellungsrahmen entsprechend färben
        self._camera_settings_frame.configure(bootstyle=status_to_bootstyle(status))
    
    def update_robotController_status(self, status):
        # Kamera-Einstellungsrahmen entsprechend färben
        self._robot_settings_frame.configure(bootstyle=status_to_bootstyle(status))
    
    def overwrite_objectDetection_settings(self, settings):
        # Einstellungen in Entry-Felder eintragen
        for key, element in self._camera_settings_entries.items():
            element.set_value(settings['camera_settings'][key])
            element.confirm_value()
        for key, element in self._camera_intrinsics_entries.items():
            element.set_value(settings['camera_intrinsics'][key])
            element.confirm_value()
        self._objects_parameters_entry.set_value(settings['objects_parameters']['min_depth'])
        self._objects_parameters_entry.confirm_value()
    
    def overwrite_robotController_settings(self, settings):
        # Einstellungen in Entry-Felder eintragen
        for key, element in self._server_entries.items():
            element.set_value(settings['server'][key])
            element.confirm_value()
        for key, element in self._cam_pos_entries.items():
            element.set_value(settings['initial_camera_pose'][key])
            element.confirm_value()

############################################################
# Applikation                                              #
############################################################

class Application(ttkb.Window):
    
    def __init__(self):
        # Fenster initialisieren
        ttkb.Window.__init__(self, themename='cosmo')
        
        # Fenster-Einstellungen vornehmen
        self.geometry('1800x865')
        self.resizable(width=False, height=False)
        self.title("Teile Greifer")
        
        # Bilder-Variablen mit einem Testbild initialisieren
        self._img_raw = Image.open('Bilder/Testbild.png')
        self._img_blur = Image.open('Bilder/Testbild.png')
        self._img_binary = Image.open('Bilder/Testbild.png')
        self._img_overlay = Image.open('Bilder/Testbild.png')
        
        # Ein Notebook erstellen und im Fenster plazieren
        self._notebook = ttkb.Notebook(self, style='secondary')
        self._notebook.pack(fill='both', expand=1)
        
        # Seiten erstellen
        self._controller_page = ControllerPage(self)
        self._detection_parameters_page = DetectionParametersPage(self)
        self._settings_page = SettingsPage(self)
        
        # Seiten plazieren
        self._controller_page.pack(fill='both', expand=1)
        self._detection_parameters_page.pack(fill='both', expand=1)
        self._settings_page.pack(fill='both', expand=1)
        
        # Seiten dem Notizbuch hinzufügen
        self._notebook.add(self._controller_page, text="Greifsteuerung")
        self._notebook.add(self._detection_parameters_page, text="Bilderkennung: Parameter einstellen")
        self._notebook.add(self._settings_page, text="Einstellungen")
        
        # Testbilder einfügen
        self._update_images()
    
    def bind_controller_functions(self, update_cv_parameters, save_cv_parameters, retry_objectDetection, retry_robotController, grab_object_at_uv, return_object_at_uv_info):
        # Callback-Funktionen des Controllers an die benötigten Stellen weiterleiten
        self._detection_parameters_page.bind_update_cv_parameters_func(update_cv_parameters)
        self._detection_parameters_page.bind_save_cv_parameters_func(save_cv_parameters)
        self._settings_page.bind_retry_objectDetection_func(retry_objectDetection)
        self._settings_page.bind_retry_robotController_func(retry_robotController)
        self._controller_page.bind_grab_object_at_uv_func(grab_object_at_uv)
        self._controller_page.bind_return_object_at_uv_info_func(return_object_at_uv_info)
    
    def overwrite_cv_parameters(self, parameters):
        # Slider der Einstellungs-Seite auf die Werte der vorgegebenen Einstellung setzten
        self._detection_parameters_page.overwrite_parameters(parameters)
    
    def set_images(self, img_raw, img_blur, img_binary, img_overlay):
        # Bilder konvertieren
        self._img_raw = self._convert_image(img_raw)
        self._img_blur = self._convert_image(img_blur)
        self._img_binary = self._convert_image(img_binary)
        self._img_overlay = self._convert_image(img_overlay)
        
        # Bilder aktualisieren
        self._update_images()
    
    def update_systems_status(self, objectDetection_status, robotController_status, rob_status):
        self._settings_page.update_objectDetection_status(objectDetection_status)
        self._settings_page.update_robotController_status(robotController_status)
        self._controller_page.update_status(objectDetection_status, rob_status)
    
    def overwrite_objectDetection_settings(self, settings):
        self._settings_page.overwrite_objectDetection_settings(settings)
    
    def overwrite_robotController_settings(self, settings):
        self._settings_page.overwrite_robotController_settings(settings)
    
    def _convert_image(self, img):
        # Von BGR nach RGB ändern
        img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
        
        # In ein Bild umwandeln
        img = Image.fromarray(img)
        
        # Bild zurückgeben
        return img
    
    def _update_images(self):
        # Bilder auf den Seiten aktualisieren
        self._controller_page.update_images(self._img_raw, self._img_overlay)
        self._detection_parameters_page.update_images(self._img_raw, self._img_blur, self._img_binary, self._img_overlay)

############################################################
# Test                                                     #
############################################################

if __name__ == "__main__":
    # Applikation ohne Controller starten
    app = Application()
    app.mainloop()