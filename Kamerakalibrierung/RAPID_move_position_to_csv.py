path_rapid = "Kamerakalibrierung (Matlab)\cam_calib_12_06\Camera_Calibration_Positions.mod"
path_csv = "Kamerakalibrierung (Matlab)\cam_calib_12_06\Pose_data.csv"



with open(path_rapid, 'r') as file_rapid:
    rapid_lines = file_rapid.readlines()

with open(path_csv, 'w') as file_csv:
    file_csv.write("x, y, z, q1, q2, q3, q4\n")
    for line in rapid_lines:
        start_index = line.find("MoveL")

        if start_index == -1:
            continue
        start_index = start_index + 8
        line = line[start_index:].replace('],[', ',')
        parts = line.split(',')
        for i in range(6):
            file_csv.write(f"{parts[i]}, ")
        file_csv.write(f"{parts[6]}\n")