# Dieses Program enthält die Robotersteuerung für die
# automatische Greifsoftware.
#
# Autor: Maximilian Schnell

############################################################
# Bibliotheken                                             #
############################################################

# Windows-Sockets (TCP/IP-Kommunikation)
import socket
# Multithreading
import threading
import queue
# Modul-Status-Enum
from utils import Status, RobotStatus

############################################################
# Konstanten                                               #
############################################################

HEADER_MSG_TYPE_SIZE = 3
HEADER_MSG_LENGTH_SIZE = 2
STATUS_MSG_SIZE = 1


############################################################
# Exception-Klassen                                        #
############################################################

class SocketError(Exception):
    pass

class RobotStateError(Exception):
    pass

class UnexpectedMessageError(Exception):
    pass

############################################################
# Code                                                     #
############################################################

class RobotController(threading.Thread):
    
    def __init__(self, server_ip, server_port, cam_position):
        # Variablen abspeichern
        self._server_ip = server_ip
        self._server_port = server_port
        self._position = [cam_position['x'], cam_position['y'], cam_position['z'], cam_position['gamma']]
        
        # Variablen initialisieren
        self._status = RobotStatus.NOT_CONNECTED
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Thread-Sicherheitsobjekte initialisieren
        self._stop_event = threading.Event()
        self._status_lock = threading.Lock()
        self._position_lock = threading.Lock()
        self._socket_lock = threading.Lock()
        self._command_queue = queue.Queue(1)
        
        # Thread starten
        super().__init__(daemon=True, name="RobotController")
    
    def get_status(self):
        # Gleichzeitiges Zugreifen verhindern
        with self._status_lock:
            if self._status == RobotStatus.NOT_CONNECTED:
                return Status.UNKNOWN
            elif self._status == RobotStatus.ERROR:
                return Status.ERROR
            else:
                return Status.WORKING
    
    def get_robot_status(self):
        # Gleichzeitiges Zugreifen verhindern
        with self._status_lock:
            return self._status
    
    def get_extrinsics(self):
        # Gleichzeitiges Zugreifen verhindern
        with self._status_lock:
            # Ist der Roboter in einer bekannten Position? (ist nur bei WAITING bekannt)
            position_is_known = (self._status == RobotStatus.WAITING)
        
        # Fehler melden, falls unbekannt
        if position_is_known:
            # Gleichzeitiges Zugreifen verhindern
            with self._position_lock:
                return True, self._position
        else:
            return False, None
    
    def move_camera(self, delta_x, delta_y, delta_z, delta_gamma):
        # Befehl erstellen
        with self._position_lock:
            command = lambda: self._send_move_camera_command(self._position + [delta_x, delta_y, delta_z, delta_gamma])
        
        # Befehl in Befehl-Queue packen (ggf. ersetzten)
        self._put_command_in_queue(command)
    
    def grab_object(self, grab_data):
        # Befehl erstellen
        command = lambda: self._send_grab_object_command(grab_data)
        
        # Befehl in Befehl-Queue packen (ggf. ersetzten)
        self._put_command_in_queue(command)
    
    def stop(self):
        # Stop-Event setzen -> Thread wird beim nächsten Loop aufhören
        self._stop_event.set()
    
    def run(self):
        # Start-Prozess durchlaufen
        self._startup_procedure()
        
        # Wiederholen, solange das stop-Event nicht gesetzt wurde
        while not self._stop_event.is_set():
            # Abfragen, ob ( / Abwarten, bis) ein Befehl vorhanden ist
            command = self._command_queue.get()
            
            # Versuchen, den Befehl auszuführen
            try:
                command()
            except SocketError as e:
                print(e)
                # Verbindungsfehler könnte zu unbekanntem Zustand führen -> lieber abbrechen
                self.stop()
            except UnexpectedMessageError as e:
                print(e)
                # Fehler bei den Statusnachrichten könnte auf asynchronen Zustand deuten (oder sogar Fehlermeldung) -> lieber abbrechen
                self.stop()
            except RobotStateError as e:
                # Falscher Roboter-Status für den Befehl wurde erkannt -> harmlos, Befehl überspringen (nicht abbrechen)
                print(e)
        
        self._shutdown()
    
    def _startup_procedure(self):
        # Versuchen, sich mit dem Server zu verbinden
        try:
            self._connect_to_server()
        except SocketError as e:
            print(e)
            self.stop()
            return
        
        # Auf Bestätigungen / Statusmeldungen warten
        try:
            self._receive_status(RobotStatus.STARTUP, timeout=2)
        except UnexpectedMessageError as e:
            print(e)
            self.stop()
            return
        except SocketError as e:
            print(e)
            self.stop()
            return
        
        # Kamera in Startposition bringen
        try:
            with self._position_lock:
                start_position = self._position
            
            self._send_move_camera_command(start_position)
        except SocketError as e:
            print(e)
            self.stop()
            return
    
    def _connect_to_server(self):
        # Server-Adresse
        server_addr = (self._server_ip, self._server_port)
        
        try:
            # Gleichzeitiges Zugreifen verhindern
            with self._socket_lock:
                # Maximale Dauer für die Suche nach einer Verbindung
                self._socket.settimeout(5)
                
                # Mit dem Server (= Roboter) verbinden
                self._socket.connect(server_addr)
                
                # Timeout zurücksetzten
                self._socket.settimeout(None)
        except socket.timeout:
            # Fehler melden
            raise SocketError(f"Timeout beim Verbinden mit dem Server {server_addr}.")
        except OSError as e:
            raise SocketError(f"Ein Fehler ist beim Verbinden mit dem Server {server_addr} aufgetreten. {e}")

    def _put_command_in_queue(self, command):
        # Befehl in Befehl-Queue packen (ggf. ersetzten)
        if not self._command_queue.empty():
            try:
                self._command_queue.get_nowait()
            except queue.Empty:
                pass
        self._command_queue.put(command)

    def _send_move_camera_command(self, position):
        # Gleichzeitiges Zugreifen verhindern
        with self._status_lock:
            # Ist der Roboter bereit?
            ready = (self._status == RobotStatus.WAITING) or (self._status == RobotStatus.STARTUP)
            
            # Fehler melden, falls nicht breit
            if not ready:
                raise RobotStateError(f"Roboter-Status muss WAITING oder STARTUP entsprechen.\nself._status = {self._status.name}")
        
        # Move-Befehl senden
        try:
            # Befehls-Schlüssel senden
            with self._socket_lock:
                self._socket.send("cam".encode("utf-8"))
                
                # x, y, z und gamma senden
                self._send_with_length_header(position[0])
                self._send_with_length_header(position[1])
                self._send_with_length_header(position[2])
                self._send_with_length_header(position[3])
        except socket.error:
            raise SocketError(f"Fehler beim Senden der Kameraposition {position}.")
            
        # Auf Bestätigungen / Statusmeldungen warten
        try:
            self._receive_status(RobotStatus.MOVING_CAMERA)
            self._receive_status(RobotStatus.WAITING)
        except UnexpectedMessageError:
            raise
        except SocketError:
            raise
        
        # Position aktualisieren
        with self._position_lock:
            self._position = position
    
    def _send_grab_object_command(self, grab_data):
        # Gleichzeitiges Zugreifen verhindern
        with self._status_lock:
            # Ist der Roboter bereit zum Greifen?
            ready = (self._status == RobotStatus.WAITING)
            
            # Fehler melden, falls nicht breit
            if not ready:
                raise RobotStateError(f"Roboter-Status muss WAITING entsprechen.\nself._status = {self._status.name}")
        
        # Grab-Befehl senden
        try:
            # Befehls-Schlüssel senden
            with self._socket_lock:
                self._socket.send("grb".encode("utf-8"))
                
                # Position (x, y, z), Winkel (gamma), Breite und Höhe senden
                self._send_with_length_header(grab_data['x'])
                self._send_with_length_header(grab_data['y'])
                self._send_with_length_header(grab_data['z'])
                self._send_with_length_header(grab_data['gamma'])
                self._send_with_length_header(grab_data['w'])
                self._send_with_length_header(grab_data['h'])
        except socket.error:
            raise SocketError(f"Fehler beim Senden einer Greifposition.")
            
        # Auf Bestätigungen / Statusmeldungen warten
        try:
            self._receive_status(RobotStatus.GRABBING)
            self._receive_status(RobotStatus.MOVING_PLACE)
            self._receive_status(RobotStatus.PLACING)
            self._receive_status(RobotStatus.MOVING_CAMERA)
            self._receive_status(RobotStatus.WAITING)
        except UnexpectedMessageError:
            raise
        except SocketError:
            raise
    
    def _receive_status(self, expected_status, timeout=20):
        try:
            # Gleichzeitiges Zugreifen verhindern
            with self._socket_lock:
                # Timeout einstellen
                self._socket.settimeout(timeout)
                
                # Den Nachrichtenkopf mit dem Nachrichtentyp empfangen
                msg_type = self._socket.recv(HEADER_MSG_TYPE_SIZE).decode('utf-8')
                
                # Je nach Nachrichtentyp:
                match msg_type:
                    case 'sta':
                        # Statusnachricht empfangen
                        status_code = self._socket.recv(STATUS_MSG_SIZE).decode('utf-8')
                        try:
                            status = RobotStatus(int(status_code))
                        except Exception:
                            raise UnexpectedMessageError(f"Fehler beim umwandeln der Nachricht '{status_code}' zu einem Status-Code.")
                        
                        # Entspricht der Status dem erwarteten Status?
                        if status != expected_status:
                            # Fehler melden
                            raise UnexpectedMessageError(f"Der Status {status.name} enspricht nicht dem erwarteten Status {expected_status.name}")
                        
                        # Status aktualisieren
                        with self._status_lock:
                            self._status = status
                        
                    case 'err':
                        # Nachrichtenlänge bestimmen
                        header = self._socket.recv(HEADER_MSG_LENGTH_SIZE).decode('utf-8')
                        try:
                            msg_len = int(header)
                        except ValueError:
                            raise UnexpectedMessageError(f"Fehler beim umwandeln des Headers '{header}' zur Nachrichtenlänge.")
                        
                        # Fehlernachricht empfangen
                        err_msg = self._socket.recv(msg_len).decode('utf-8')
                        
                        # Fehler melden
                        raise UnexpectedMessageError(f"Der Roboter hat die Fehlernachricht:\n{err_msg}\ngesendet.")
                    
                    case _:
                        # Fehler melden
                        raise UnexpectedMessageError(f"Der Typ '{msg_type}' im Nachrichten-Header konnte nicht erkannt werden.")
                
        except socket.timeout:
            raise SocketError(f"Timeout beim Warten auf Status {expected_status.name}")
    
    def _send_with_length_header(self, msg):
        # Achtung: Der self._socket_lock  muss im Code bereits erworben sein, wenn diese Funktion aufgerufen werden soll!!!
        
        # Sichergehen, dass es sich um einen String handelt
        msg = str(msg)
        
        # Den Length-Header vor die Nachricht packen
        msg = f"{len(msg):<{HEADER_MSG_LENGTH_SIZE}}" + msg
        
        # Nachricht senden
        try:
            self._socket.send(msg.encode("utf-8"))
        except socket.error:
            raise
    
    def _shutdown(self):
        # Status auf ERROR setzten
        with self._status_lock:
            self._status = RobotStatus.ERROR
        
        # Socket schließen
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        finally:
            self._socket.close()
    
    def __del__(self):
        self._shutdown()