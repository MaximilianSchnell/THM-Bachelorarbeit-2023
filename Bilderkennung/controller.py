# Dieses Program enthält den Controller für die automatische
# Greifsoftware, welche die Schnittstelle zwischen der
# Darstellung (View) und den Systemen (Model) bildet.
#
# Autor: Maximilian Schnell

############################################################
# Bibliotheken                                             #
############################################################

# Einstellungsverwaltung im .yaml-Format
import yaml
# Applikation (View)
from application import Application
# Bilderkennung (Model)
from objectDetection import ObjectDetection
# Roboterkommunikation (Model)
from robotController import RobotController

############################################################
# Konstanten                                               #
############################################################

DEFAULT_CONFIG = {
    'camera_settings': {
        'camera_index': 0,
        'width': 1920,
        'height': 1080
    },
    'camera_intrinsics': {
        'fx': 1436.163640281333,
        'fy': 1442.726289971857,
        'cx': 962.7635882992781,
        'cy': 506.1877095112721,
        'k1': 0.030879754719235,
        'k2': -0.091482467868427,
        'p1': -0.002232927599662,
        'p2': 0.000545642267413
    },
    'cv_parameters': {
        'blur_kernel_size': 13,
        'threshold_brightness': 180,
        'contour_min_area': 5000,
        'contour_max_area': 20000,
        'polygon_epsilon': 0.05
    },
    'server': {
        'ip': '192.168.133.1',
        'port': 2023
    },
    'initial_camera_pose': {
        'x': 160.0,
        'y': 470.0,
        'z': 550.0,
        'gamma': 0.0
    },
    'objects_parameters': {
        'min_depth': 5.0
    }
}


############################################################
# Code                                                     #
############################################################

class Controller:
    
    def __init__(self):
        # Einstellungen laden
        self._init_settings()
        
        # Module initialisieren
        self._init_app()
        self._init_objectDetection()
        self._init_robotController()
        
        # Den Loop starten
        self._app.after(10, self.update)
        self._app.mainloop()
    
    def update(self):
        # Modul-Status in App aktualisieren
        self._app.update_systems_status(self._objectDetection.get_status(), self._robotController.get_status(), self._robotController.get_robot_status())
        
        # Falls neue Bilder vorhanden sind, diese holen und an App weitergeben
        available = self._objectDetection.update()
        
        if available:
            img_raw, img_blur, img_binary, img_overlay = self._objectDetection.get_images()
            # TODO: Braucht zu lange
            self._app.set_images(img_raw, img_blur, img_binary, img_overlay)
        
        # Nächstes Update in Warteschlange packen
        self._app.after(50, self.update)
    
    ##### Event-Funktionen #####
    
    def grab_object_at_uv(self, u_rel, v_rel):
        # Greifdaten berechnen
        hit, info = self.get_object_at_uv_info(u_rel, v_rel)
        
        # Greifen
        if hit:
            self._robotController.grab_object(info['grab_data'])
    
    def get_object_at_uv_info(self, u_rel, v_rel):
        # Position abfragen
        known, extrinsics = self._robotController.get_extrinsics()
        
        # Wenn die Position bekannt ist => Roboter ist auch fürs Greifen bereit
        if known:
            # Object holen, falls es eins an der gedrückten Position gibt
            hit, obj = self._objectDetection.get_object_at_uv(u_rel, v_rel)
            
            if hit:
                grab_data = self._objectDetection.get_grab_data(obj, extrinsics)
                return True, {'picture_info': obj, 'grab_data': grab_data}
        
        return False, None
    
    ##### Modulinitialisierungs-Funktionen #####
    
    def _init_app(self):
        # Applikation erstellen
        self._app = Application()
        self._app.bind_controller_functions(update_cv_parameters=self.update_cv_parameters,
                                            save_cv_parameters=self.save_cv_parameters,
                                            retry_objectDetection=self.retry_objectDetection,
                                            retry_robotController=self.retry_robotController,
                                            grab_object_at_uv=self.grab_object_at_uv,
                                            return_object_at_uv_info=self.get_object_at_uv_info)
        self._app.overwrite_cv_parameters(self._config['cv_parameters'])
        self._app.overwrite_objectDetection_settings({'camera_settings': self._config['camera_settings']} | {'camera_intrinsics': self._config['camera_intrinsics']} | {'objects_parameters': self._config['objects_parameters']})
        self._app.overwrite_robotController_settings({'server': self._config['server']} | {'initial_camera_pose': self._config['initial_camera_pose']})
    
    def retry_objectDetection(self, settings):
        # Settings in config eintragen und speichern
        self._config = self._config | settings
        self._save_settings()
        
        # Bilderkennung neu starten
        del self._objectDetection
        self._init_objectDetection()
    
    def _init_objectDetection(self):
        # Bilderkennung starten
        self._objectDetection = ObjectDetection(
            self._config['camera_settings'],
            self._config['camera_intrinsics'],
            self._config['cv_parameters'],
            self._config['objects_parameters'])
    
    def retry_robotController(self, settings):
        # Settings in config eintragen und speichern
        self._config = self._config | settings
        self._save_settings()
        
        # Bilderkennung neu starten
        del self._robotController
        self._init_robotController()
    
    def _init_robotController(self):
        # Robotersteuerung starten
        self._robotController = RobotController(
            self._config['server']['ip'],
            self._config['server']['port'],
            self._config['initial_camera_pose'])
        self._robotController.start()
    
    ##### Einstellungsverwaltungs-Funktionen #####
    
    def update_cv_parameters(self, parameters):
        # Einstellungen an die Bilderkennung weitergeben
        self._objectDetection.set_cv_parameters(parameters)
        
    def save_cv_parameters(self, parameters):
        # Einstellungen abspeichern
        self._config['cv_parameters'] = parameters
        self._save_settings()
    
    def _init_settings(self):
        # Standard-Einstellungen laden
        self._config = DEFAULT_CONFIG
        
        # Config-Datei einlesen, falls vorhanden
        self._load_settings()
    
    def _save_settings(self, path="config.yaml"):
        # Einstellungen in Config-Datei abspeichern
        with open(path, 'w') as configFile:
            yaml.dump(self._config, configFile, sort_keys=False)
    
    def _load_settings(self, path="config.yaml"):
        # Einstellungen aus Config-Datei laden
        try:
            with open(path, 'r') as configFile:
                # Die neuen Einstellungen mit den alten zusammenführen
                self._config = self._config | yaml.safe_load(configFile)
        except:
            pass
        
        # Einstellungen abspeichern, falls die Einstellungen importiert wurden
        isImport = (path == "config.yaml")
        if isImport:
            self._save_settings()


############################################################
# Startsequenz                                             #
############################################################

if __name__ == "__main__":
    controller = Controller()