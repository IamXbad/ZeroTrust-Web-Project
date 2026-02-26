function devices = device_registry()
    % Create a registry of trusted devices
    devices = containers.Map();

    % Read trusted devices from file
    fid = fopen('trusted_devices.txt', 'r');

    if fid == -1
        return;
    end

    tline = fgetl(fid);
    while ischar(tline)
        devices(strtrim(tline)) = true;
        tline = fgetl(fid);
    end

    fclose(fid);
end