function response = edge_server(deviceID, token, data)

    % Load trusted devices
    devices = device_registry();

    % Open log file
    fid = fopen('edge_logs.txt', 'a');
    timestamp = datestr(now);

    % Step 1: Verify device identity
    if ~isKey(devices, deviceID)
        fprintf(fid, "[%s] BLOCKED: Unknown device %s\n", timestamp, deviceID);
        fclose(fid);
        response = "Access Denied: Unknown Device";
        return;
    end

    % Step 2: Zero-Trust token verification
    if ~strcmp(token, "VALID")
        fprintf(fid, "[%s] BLOCKED: Invalid token from %s\n", timestamp, deviceID);
        fclose(fid);
        response = "Access Denied: Invalid Token";
        return;
    end

    % Step 3: Accept data
    fprintf(fid, "[%s] ACCEPTED: %s | Data: %s\n", timestamp, deviceID, data);
    fclose(fid);

    response = "Data Accepted and Forwarded";
end