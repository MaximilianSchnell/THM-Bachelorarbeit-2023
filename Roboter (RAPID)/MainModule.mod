MODULE MainModule

    ! Externe Einstellungen (sollten nach Kalibrierung verändert werden)
    
    ! Werkzeuge
    PERS tooldata tool_camera := [TRUE,[[91.899680,-16.803906,172.227258],[0.769835,-0.069431,-0.051756,0.632341]],[3.1,[0,0,120],[1,0,0,0],0,0,0]];
    PERS tooldata tool_grabber := [TRUE,[[0,0,445],[1,0,0,0]],[3.1,[0,0,120],[1,0,0,0],0,0,0]];
    
    ! Werkobjekt-Koordinatensysteme
    PERS wobjdata wobj_grab := [FALSE,TRUE,"",[[0,0,0],[1,0,0,0]],[[663.111,970.525,364.373],[0.697527,0.00846819,0.00460813,0.716493]]];
    PERS wobjdata wobj_place := [FALSE,TRUE,"",[[0,0,0],[1,0,0,0]],[[1068.54,-75.259,197.469],[0.707878,-0.000120477,0.00112396,0.706334]]];
    
    ! Sicherheitsposition (Position zu der immer sicher gefahren werden kann; Basiskoordinaten; tool0)
    PERS robtarget p_safe := [[668.16,546.62,961.00],[2.65525E-06,0.778434,0.627727,-4.47178E-05],[0,-1,1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
    
    ! Sicherheitsabstand für die Anfahrt zum Greif und Ablageort
    PERS num safe_z_distance := 60;
    
    ! Ablageort: Größe der Ablagefläche
    PERS num place_min_x := 0;
    PERS num place_min_y := 0;
    PERS num place_max_x := 500;
    PERS num place_max_y := 130;
    PERS num place_spacing := 10;
    
    ! Bewegung
    PERS speeddata speed_travel := [200,500,0,0];
    PERS speeddata speed_positioning := [200,500,0,0];
    PERS speeddata speed_pick_place := [50,500,0,0];
    
    ! Socket-Kommunikation
	PERS string server_ip := "192.168.133.1";
	PERS num server_port := 2023;
    
    ! Interne Einstellungen / Variablen (sollten nicht geändert werden)
    
    ! Socket-Kommunikation
	CONST num HEADER_MSG_TYPE_SIZE := 3;
    CONST num HEADER_MSG_LENGTH_SIZE := 2;
	VAR socketdev server_socket;
	VAR socketdev client_socket;
	VAR string client_ip;
    
    ! Positionen
    VAR robtarget p_camera;
    
    ! Ablageort
    VAR num place_running_x;
    VAR num place_running_y;
    VAR num place_running_w;
    
    ! Ablauf
    VAR bool mainloop_active;
    
    PROC main()
        ! FlexPendant-Anzeige zurücksetzen
        TPErase;
        
        ! Server starten
        start_server;
        
        ! Auf Verbindung warten
		SocketAccept server_socket, client_socket \ClientAddress := client_ip \Time := WAIT_MAX;
        
        ! Status auf dem FlexPendant anzeigen
		TPWrite "[STATUS] Verbindung mit " + client_ip + " wurde hergestellt!";
        
        send_status 1;
        
        ! Auf Sicherheitsposition fahren
        MoveL p_safe, speed_positioning, fine, tool0;
        
        ! Ablageort auf Start setzen
        place_running_x := place_min_x;
        place_running_y := place_min_y;
        place_running_w := 0;

        ! Die Hauptschleife starten
        mainloop;
        
        ! Immer Verbindung und Server wieder schließen
        SocketClose client_socket;
		SocketClose server_socket;
    ERROR
	    SocketClose client_socket;
	    SocketClose server_socket;
        RAISE;
	ENDPROC
    
    PROC start_server()
        ! Status auf dem FlexPendant anzeigen
		TPWrite "[STATUS] Der TCP/IP-Server startet!";
        
        ! Server-Socket-Objekt erstellen
		SocketCreate server_socket;
        
        ! Server starten
		SocketBind server_socket, server_ip, server_port;
		SocketListen server_socket;
        
        ! Status auf dem FlexPendant anzeigen
		TPWrite "[STATUS] Der TCP/IP-Server ist bereit und wartet auf eine Verbindung!";
	ENDPROC
    
    PROC mainloop()
        ! Variablen deklarieren
        VAR string receive_string;
        
        ! Konfigurationskontrolle für MoveL
        ConfL \Off;
        
        ! Schleife starten
        mainloop_active := TRUE;
		WHILE mainloop_active DO
            ! Befehl-Typ empfangen
            SocketReceive client_socket \Str := receive_string \ReadNoOfBytes := HEADER_MSG_TYPE_SIZE \Time := WAIT_MAX;
            
            TEST receive_string
            CASE "cam":
                ! Parameter für Kamerabewegung empfangen und ausführen
                receive_and_move_cam;
            CASE "grb":
                ! Parameter für Greif- und Plaziervorgang empfangen und ausführen
                receive_and_grab_and_place;
            DEFAULT:
                send_and_display_error "Falschen Nachrichten-Typ erhalten: '" + receive_string + "'";
                mainloop_active := FALSE;
            ENDTEST
        ENDWHILE
        
        ERROR
            RAISE;
    ENDPROC
    
    FUNC num receive_number()
		VAR string receive_string;
		VAR num msg_length;
        VAR num value;
		
		! Header mit Länge empfangen
		SocketReceive client_socket \Str := receive_string \ReadNoOfBytes := HEADER_MSG_LENGTH_SIZE \Time := WAIT_MAX;
		
        ! Header in Wert (Nachrichtenlänge) umwandeln
		IF NOT StrToVal(receive_string, msg_length) THEN
			send_and_display_error "Fehler bei der Konvertierung von '" + receive_string + "' in eine Zahl";
		ENDIF
		
		! Nachricht empfangen
		SocketReceive client_socket \Str := receive_string \ReadNoOfBytes := msg_length;
		
        ! Nachricht in Wert umwandeln
		IF NOT StrToVal(receive_string, value) THEN
			send_and_display_error "Fehler bei der Konvertierung von '" + receive_string + "' in eine Zahl";
		ENDIF
		
		RETURN value;
	ENDFUNC
    
    PROC receive_and_move_cam()
        ! Variablen deklarienen
        VAR num x;
        VAR num y;
        VAR num z;
        VAR num gamma;
        
        ! Parameter für Kamerabewegung empfangen
        x := receive_number();
        y := receive_number();
        z := receive_number();
        gamma := receive_number();
        
        ! Kamera an Position bewegen
        move_cam x, y, z, gamma;
    ENDPROC
    
    PROC move_cam(num x, num y, num z, num gamma)
        ! Status-Nachricht MOVING_CAMERA senden
        send_status 2;
        
        ! Kamera-Position berechnen und speichern
        p_camera := get_robtarget(x, y, z, gamma);
        
        ! Kamera Positionieren
        MoveL p_camera, speed_positioning, fine, tool_camera, \WObj := wobj_grab;
        
        ! Status-Nachricht WAITING senden
        send_status 3;
    ENDPROC
    
    PROC receive_and_grab_and_place()
        ! Variablen deklarienen
        VAR num x;
        VAR num y;
        VAR num z;
        VAR num gamma;
        VAR num w;
        VAR num h;
        
        ! Parameter für Greif- und Plaziervorgang empfangen
        x := receive_number();
        y := receive_number();
        z := receive_number();
        gamma := receive_number();
        w := receive_number();
        h := receive_number();
        
        ! Objekt greifen und plazieren
        grab_and_place x, y, z, gamma, w, h;
    ENDPROC
    
    PROC grab_and_place(num x, num y, num z, num gamma, num w, num h)
        ! Variablen deklarieren
        VAR robtarget p_place;
        VAR robtarget p_object;
        
        ! Ablageposition berechnen (damit nicht gegriffen wird, wenn kein Ablageplatz frei ist)
        IF place_running_y + h > place_max_y THEN
            ! Neue Spalte beginnen
            place_running_x := place_running_x + place_spacing + place_running_w;
            place_running_y := place_min_y;
            place_running_w := 0;
        ENDIF
        IF place_running_x + w > place_max_x THEN
            ! Ablagebereich ist voll
            send_and_display_error "Ablagebereich ist voll!";
            RETURN;
        ENDIF
        p_place := get_robtarget(place_running_x + w / 2, place_running_y + h / 2, z, 90);
        place_running_y := place_running_y + place_spacing + h;
        IF place_running_w < w THEN
            place_running_w := w;
        ENDIF
        
        ! Objekt-Position berechnen
        p_object := get_robtarget(x, y, z, gamma);
        
        ! Status-Nachricht GRABBING senden
        send_status 4;
        
        ! Greifer über Objekt positionieren
        MoveL Offs(p_object, 0, 0, safe_z_distance), speed_travel, z20, tool_grabber, \WObj := wobj_grab;
        
        ! Greifer auf Objekt positionieren
        MoveL p_object, speed_pick_place, fine, tool_grabber, \WObj := wobj_grab;
        
        ! Objekt greifen
        Set VAKUUM;
        WaitTime 0.5;
        
        ! Objekt anheben
        MoveL Offs(p_object, 0, 0, safe_z_distance), speed_pick_place, z20, tool_grabber, \WObj := wobj_grab;
        
        ! Status-Nachricht MOVING_PLACE senden
        send_status 5;
        
        ! Über Ablageposition fahren
        MoveL p_safe, speed_travel, z50, tool0;
        MoveL Offs(p_place, 0, 0, safe_z_distance), speed_travel, z20, tool_grabber, \WObj := wobj_place;
        
        ! Status-Nachricht PLACING senden
        send_status 6;
        
        ! Objekt absetzten
        MoveL p_place, speed_pick_place, fine, tool_grabber, \WObj := wobj_place;
        
        ! Objekt loslassen
        Reset VAKUUM;
        WaitTime 0.5;
        
        ! Greifer weg bewegen
        MoveL Offs(p_place, 0, 0, safe_z_distance), speed_pick_place, z20, tool_grabber, \WObj := wobj_place;
        
        ! Status-Nachricht MOVING_CAMERA senden
        send_status 2;
        
        ! Auf letzte Kameraposition fahren
        MoveL p_safe, speed_travel, z50, tool0;
        MoveL p_camera, speed_travel, fine, tool_camera, \WObj := wobj_grab;
        
        ! Status-Nachricht WAITING senden
        send_status 3;
    ENDPROC
    
    FUNC robtarget get_robtarget(num x, num y, num z, num gamma)
        ! Variable deklarieren
        VAR robtarget target;
        
        ! Gamma ist der Winkel um die z-Achse
        target := [[x, y, z],OrientZYX(gamma-90, 0, 180),[-1,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
        RETURN target;
    ENDFUNC
    
    PROC send_status(num i)
        ! Variable deklarieren
        VAR string message;
        
        ! Status senden
        message := "sta" + NumToStr(i, 0);
        SocketSend client_socket \Str := message;
    ENDPROC
    
    PROC send_and_display_error(string msg)
        ! Variable deklarieren
        VAR string message;
        
        ! Fehlernachricht senden und auf PHG anzeigen
        message := "err" + msg;
        SocketSend client_socket \Str := message;
        TPWrite "[ERROR] " + msg;
    ENDPROC
    
ENDMODULE