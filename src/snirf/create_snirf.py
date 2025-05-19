import pandas as pd
import numpy as np
import h5py
import os
import shutil
import io

def create_snirf(csv_filename):
    uploads_dir = 'src/uploads'
    output_dir = 'src/snirf/snirf_outputfiles'
    csv_path = os.path.join(uploads_dir, csv_filename)

    if not os.path.exists(csv_path):
        print(f"[ERROR] File not found: {csv_path}")
        return None, None

    # Read metadata lines
    with open(csv_path, 'r') as f:
        lines = f.readlines()

    metadata_lines = lines[:9]
    metadata = {line.split(',')[0].strip(): line.split(',', 1)[1].strip() for line in metadata_lines if ',' in line}

    # Extract metadata fields
    hardware_version = metadata.get("Hardware Version", "")
    firmware_version = metadata.get("Firmware Version", "")
    led_current = metadata.get("NIR LED Emitter Current", "")
    adc_gain = metadata.get("ADC Gain", "")
    measurement_date = metadata.get("Date", "")
    measurement_time = metadata.get("Time", "")

    # Parse tabular data
    data_lines = lines[9:]
    data_io = io.StringIO("".join(data_lines))
    raw_data = pd.read_csv(data_io)

    print("[INFO] Tabular data loaded successfully.")

    # Define headers explicitly
    headers = [
        'Time', 'System Time (s)', 'Sample Time (s)',
        *[f'LED_A_{wl}_DET{i}' for wl in [782, 801, 808, 828, 848, 887] for i in range(1, 4)],
        *[f'LED_A_DARK_DET{i}' for i in range(1, 4)],
        *[f'LED_B_{wl}_DET{i}' for wl in [782, 801, 808, 828, 848, 887] for i in range(1, 4)],
        *[f'LED_B_DARK_DET{i}' for i in range(1, 4)],
        'Accelerometer X axis', 'Accelerometer Y axis', 'Accelerometer Z axis',
        'Gyroscope X axis', 'Gyroscope Y axis', 'Gyroscope Z axis',
        'PCB Temp', 'Skin Temp'
    ]
    raw_data.columns = headers
    raw_data = raw_data.apply(pd.to_numeric, errors='coerce')

    # Extract signals
    accelerometer = raw_data[['Accelerometer X axis', 'Accelerometer Y axis', 'Accelerometer Z axis']].astype(np.float32).to_numpy()
    gyroscope = raw_data[['Gyroscope X axis', 'Gyroscope Y axis', 'Gyroscope Z axis']].astype(np.float32).to_numpy()
    pcb_temp = raw_data[['PCB Temp']].astype(np.float32).to_numpy()
    skin_temp = raw_data[['Skin Temp']].astype(np.float32).to_numpy()

    # Light signals
    data_columns = [col for col in raw_data.columns if 'LED_' in col]
    signal_data = raw_data[data_columns].astype(np.float32)
    signal_column_names = np.array(signal_data.columns, dtype='S')

    # Time column
    time_data = raw_data['Time'].astype(str)
    time_data = time_data.apply(lambda x: x if len(x.split(":")) == 2 else f"00:{x}")
    time_data = np.array(time_data, dtype='S')

    # SNIRF probe info
    det_positions = np.array([[3.], [4.], [5.]])
    src_positions = np.array([[0., 8.]])
    wavelengths = np.array([782, 801, 808, 828, 848, 887], dtype=np.float32)
    distances = np.array([
        ['LED_A', 'DET_1', 'DET_2', 'DET_3', 'LED_B'],
        ['0cm', '3cm', '4cm', '5cm', '8cm'],
    ], dtype='S10')

    # Ensure clean output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for existing_file in os.listdir(output_dir):
        file_path = os.path.join(output_dir, existing_file)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"[ERROR] Could not delete {file_path}: {e}")

    # Output SNIRF file path
    snirf_filename = os.path.splitext(csv_filename)[0] + '.snirf'
    snirf_path = os.path.join(output_dir, snirf_filename)

    # Write SNIRF
    with h5py.File(snirf_path, 'w') as f:
        f.create_dataset("/formatVersion", data='1.0')

        data_group = f.create_group("nirs/data1")
        data_group.create_dataset("dataTimeSeries", data=signal_data.to_numpy())
        data_group.create_dataset("time", data=time_data)

        measurement = data_group.create_group("measurementList1")
        measurement.create_dataset("dataType", data=np.array([1]))
        measurement.create_dataset("dataTypeIndex", data=np.array([1]))
        measurement.create_dataset("detectorIndex", data=np.array([1]))
        measurement.create_dataset("sourceIndex", data=np.array([1]))
        measurement.create_dataset("wavelengthIndex", data=np.array([1]))

        meta = f.create_group("nirs/metaDataTags")
        meta.create_dataset("HardwareVersion", data=hardware_version)
        meta.create_dataset("FirmwareVersion", data=firmware_version)
        meta.create_dataset("NIR_LED_EmitterCurrent", data=led_current)
        meta.create_dataset("ADC_Gain", data=adc_gain)
        meta.create_dataset("MeasurementDate", data=measurement_date)
        meta.create_dataset("MeasurementTime", data=measurement_time)
        meta.create_dataset("VoltageUnit", data='V')
        meta.create_dataset("TimeUnit", data='s')
        meta.create_dataset("FrequencyUnit", data='Hz')
        meta.create_dataset("dataTimeSeries_Column_names", data=signal_column_names)
        meta.create_dataset("detectorSource_distance", data=distances)
        meta.create_dataset("detectorSource_distance_unit", data=np.array(['cm'], dtype='S2'))
        meta.create_dataset("Accelerometer", data=accelerometer)
        meta.create_dataset("Gyroscope", data=gyroscope)
        meta.create_dataset("PCB Temperature", data=pcb_temp)
        meta.create_dataset("Skin Temperature", data=skin_temp)

        probe = f.create_group("nirs/probe")
        probe.create_dataset("detectorLabels", data=np.array(['DET1', 'DET2', 'DET3'], dtype='S'))
        probe.create_dataset("detectorPos3D", data=det_positions)
        probe.create_dataset("sourceLabels", data=np.array(['LED_A', 'LED_B'], dtype='S'))
        probe.create_dataset("sourcePos2D", data=src_positions)
        probe.create_dataset("wavelengths", data=wavelengths)

    print(f"[SUCCESS] SNIRF file created: {snirf_path}")
    return snirf_path, snirf_filename
