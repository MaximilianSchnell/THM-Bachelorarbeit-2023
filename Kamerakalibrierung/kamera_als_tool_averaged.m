% Dieses Programm berechnet die x, y und z, sowie q1, q2, q3 und q4-Werte,
% welche benoetigt werden, um die Kamera als Werkzeug (Tool) in die
% Robotersteuerung einzutragen. Es wird davon ausgegangen, dass zuvor eine
% Kamerakalibrierung durchgefuehrt wurde und die Ergebnisse im Workspace
% als Variable unter dem Namen "cameraParams" bereits vorliegen und die zu
% den Bildern gehoerigen Roboterpositionen (Endeffektor in {Wo}-Koordinaten)
% importiert wurden.
% 
% Autor: Maximilian Schnell

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Die in Schritt 3 festgelegten Roboterpositionen eintragen:              %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Position:
x = Posedata.x;
y = Posedata.y;
z = Posedata.z;

% Rotation:
q1 = Posedata.q1;
q2 = Posedata.q2;
q3 = Posedata.q3;
q4 = Posedata.q4;

% Index der Bilder, welche bei der Kalibrierung benutzt wurden
% (aussortierte weglassen)
valid_images = 1:32;


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Die in Schritt 4 ermittelten Vektoren:                                  %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Position:
% Translationsvektor von {Wo} nach {S} in {Wo}-Koordinaten
t_Wo_S__Wo = 23 * [5 8 0]';

% Rotation:
% Koordinatenachsrichtungen von {S} in {Wo}-Koordinaten:
x_S__Wo = [0 -1 0]';
y_S__Wo = [-1 0 0]';
z_S__Wo = [0 0 -1]';


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Berechnung                                                              %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Aus allen Kalibrierposen den Translationsvektor und Rotationsquaternion
% der Kamera bestimmen

% Transformationsmatrix {Wo}/{S} berechnen (bleibt konstant)
T_Wo_S = [x_S__Wo, y_S__Wo, z_S__Wo, t_Wo_S__Wo; 0 0 0 1];

% Werte initialisieren (werden überschrieben)
t_E_K__E = zeros(length(valid_images), 3);
q_E_K = zeros(length(valid_images), 4);
weight = zeros(length(valid_images), 1);

for id_params = 1:length(valid_images)
    id_pose = valid_images(id_params);
    
    % Transformationsmatrix {E}/{Wo} berechnen
    % Rotationsquaternion {Wo}/{E}
    q_Wo_E = quaternion([q1(id_pose), q2(id_pose), q3(id_pose), q4(id_pose)]);
    % Rotationsquaternion {E}/{Wo}
    q_E_Wo = conj(q_Wo_E);
    % Quaternion in Rotationsmatrix umwandeln
    R_E_Wo = quat2rotm(q_E_Wo);
    % Translationsvektor von {Wo} nach {E} in {Wo}-Koordinaten
    t_Wo_E__Wo = [x(id_pose) y(id_pose) z(id_pose)]';
    % Translationsvektor von {E} nach {Wo} in {E}-Koordinaten berechnen
    t_E_Wo__E = - R_E_Wo * t_Wo_E__Wo;
    % Transformationsmatrix {E}/{Wo}
    T_E_Wo = [R_E_Wo, t_E_Wo__E; 0 0 0 1];
    
    % Transformationsmatrix {S}/{K} berechnen
    % Rotationsmatrix {S}/{K}
    R_S_K = cameraParams.RotationMatrices(:,:,id_params);
    % Translationsvektor von {K} nach {S} in {K}-Koordinaten
    t_K_S__K = cameraParams.TranslationVectors(id_params,:)';
    % Translationsvektor von {S} nach {K} in {S}-Koordinaten berechnen
    t_S_K__S = - R_S_K * t_K_S__K;
    % Transformationsmatrix {S}/{K}
    T_S_K = [R_S_K, t_S_K__S; 0 0 0 1];
    
    % Transformationsmatrix {E}/{K} berechnen
    T_E_K = T_E_Wo * T_Wo_S * T_S_K;

    % Zu mittelnde Werte berechnen
    % Translationsvektor von {E} nach {K} in {E}-Koordinaten
    t_E_K__E(id_params,:) = T_E_K(1:3, 4);
    % Rotationsmatrix {E}/{K}
    R_E_K = T_E_K(1:3, 1:3);
    q_E_K(id_params,:) = rotm2quat(R_E_K);
    % Gewichtung
    mean_error = mean(vecnorm(cameraParams.ReprojectionErrors(:,:,id_params)'));
    weight(id_params) = 1 / mean_error;
end

% Mittelwert berechnen
% Tool-Offset
t_E_K__E_avg = sum(t_E_K__E .* weight, 1) / sum(weight);

% Tool-Orientation
axang_E_K_avg = sum(quat2axang(q_E_K) .* weight, 1) / sum(weight);
q_E_K_avg = axang2quat(axang_E_K_avg);

% Abweichungen berechnen
% Tool-Offset
t_E_K__E_err = abs(t_E_K__E - t_E_K__E_avg);
t_E_K__E_err_min = min(t_E_K__E_err, [], 1);
t_E_K__E_err_max = max(t_E_K__E_err, [], 1);
t_E_K__E_err_std = std(t_E_K__E_err, 1);

% Tool-Orientation
q_E_K_err = abs(q_E_K - q_E_K_avg);
q_E_K_err_min = min(q_E_K_err, [], 1);
q_E_K_err_max = max(q_E_K_err, [], 1);
q_E_K_err_std = std(q_E_K_err, 1);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Ergebnis ausgeben                                                       %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Text-Ausgabe

offset_table = table(t_E_K__E_avg', t_E_K__E_err_std', ...
    'VariableNames', {'Mittelwert / mm','Standardabweichung / mm'}, ...
    'RowNames', {'x','y','z'});
orient_table = table(q_E_K_avg', q_E_K_err_std', ...
    'VariableNames', {'Mittelwert','Standardabweichung'}, ...
    'RowNames', {'q1','q2','q3','q4'});

fprintf("\nKamera-Tooldata: \n")
fprintf("\nOffset: \n")
disp(offset_table)
fprintf("\nQuaternion: \n")
disp(orient_table)
fprintf("\nPose (zusammengesetzt): \n")
fprintf("[[%f,%f,%f],[%f,%f,%f,%f]]\n", [t_E_K__E_avg q_E_K_avg])


% Ergebnis visualisieren

plotTransforms(t_E_K__E, q_E_K, 'framesize', 50, 'InertialZDirection', 'Down');
hold on
plotTransforms([0 0 0; t_E_K__E_avg], [1 0 0 0; q_E_K_avg], 'framesize', 100, 'InertialZDirection', 'Down');
xlabel('x-Achse');
ylabel('y-Achse');
zlabel('z-Achse');
axis equal;
grid on;
hold off; 