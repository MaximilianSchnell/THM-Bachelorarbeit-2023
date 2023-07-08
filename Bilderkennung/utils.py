# Dieses Program enthält Hilfsklassen für die
# automatische Greifsoftware.
#
# Autor: Maximilian Schnell

############################################################
# Bibliotheken                                             #
############################################################

# Enums
import enum


############################################################
# Modul-Zustands-Enum                                      #
############################################################

class Status(enum.Enum):
    # Modul ist noch nicht bereit
    UNKNOWN = 0
    # Modul funktioniert
    WORKING = 1
    # Modul ist gescheitert
    ERROR = 2


############################################################
# Roboter-Zustands-Enum                                    #
############################################################

class RobotStatus(enum.Enum):
    # Roboter ist noch nicht verbunden
    NOT_CONNECTED = 0
    # Roboter fährt auf eine sichere Position
    STARTUP = 1
    # Roboter positioniert die Kamera
    MOVING_CAMERA = 2
    # Roboter hat Kamera auf "Greiffeld" gerichtet und wartet auf Befehl
    WAITING = 3
    # Roboter greift das Teil
    GRABBING = 4
    # Roboter fährt über die Ablegestelle
    MOVING_PLACE = 5
    # Roboter legt das Teil ab
    PLACING = 6
    # Roboter hat Fehler zurückgegeben
    ERROR = 7