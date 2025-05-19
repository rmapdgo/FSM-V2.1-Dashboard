import numpy as np
import pandas as pd

def UCLN(data: pd.DataFrame):
    # Define wavelengths used in FSM-V2.1
    wavelengths = [782, 801, 808, 828, 848, 887]

    # Load extinction coefficients
    extinction_path = "src/concentrations_ucln_srs/defaults.csv"
    epsilon = pd.read_csv(extinction_path)

    ext_coeffs = []
    ext_coeffs_cor = []

    for wl in wavelengths:
        row = epsilon[epsilon['wavelength'] == wl]
        if not row.empty:
            ext = row[['HbO2', 'HHb', 'CCO']].values.flatten()
            corr = row['wl_dep'].values[0]
            ext_coeffs.append(ext)
            ext_coeffs_cor.append(ext * corr)
        else:
            raise ValueError(f"Wavelength {wl} not found in extinction coefficient data.")

    ext_coeffs_cor = np.array(ext_coeffs_cor)
    ext_coeffs_inv = np.linalg.pinv(ext_coeffs_cor)

    # Optode distances in mm
    optode_distance_A = np.array([30, 40, 50])
    optode_distance_B = np.array([50, 40, 30])
    DPF = 4.99

    # Parse intensity values from data
    def get_group_data(prefix, det):
        return np.stack([
            pd.to_numeric(data[f'{prefix}_{wl}_DET{det}'], errors='coerce').fillna(1e-10).values
            for wl in wavelengths
        ], axis=0)  # shape: (6, n_samples)

    group_a_1 = get_group_data('LED_A', 1)
    group_a_2 = get_group_data('LED_A', 2)
    group_a_3 = get_group_data('LED_A', 3)
    group_b_1 = get_group_data('LED_B', 1)
    group_b_2 = get_group_data('LED_B', 2)
    group_b_3 = get_group_data('LED_B', 3)

    # Compute attenuation
    def calc_attenuation(group):
        return np.log10(100 / np.clip(group, 1e-10, None))  # shape: (6, n_samples)

    att_a_1 = calc_attenuation(group_a_1)
    att_a_2 = calc_attenuation(group_a_2)
    att_a_3 = calc_attenuation(group_a_3)
    att_b_1 = calc_attenuation(group_b_1)
    att_b_2 = calc_attenuation(group_b_2)
    att_b_3 = calc_attenuation(group_b_3)

    # Delta attenuation
    def delta_atten(att):
        return att[:, 0:1] - att  # broadcast over all samples

    att_a_1 = delta_atten(att_a_1)
    att_a_2 = delta_atten(att_a_2)
    att_a_3 = delta_atten(att_a_3)
    att_b_1 = delta_atten(att_b_1)
    att_b_2 = delta_atten(att_b_2)
    att_b_3 = delta_atten(att_b_3)

    # Concentration calculation
    def get_conc(delta_att, distance):
        conc = 10000 * ext_coeffs_inv @ (delta_att / (distance * DPF))
        return pd.DataFrame(conc.T, columns=['HHb', 'HbO', 'oxCCO'])

    conc_a_1_df = get_conc(att_a_1, optode_distance_A[0])
    conc_a_2_df = get_conc(att_a_2, optode_distance_A[1])
    conc_a_3_df = get_conc(att_a_3, optode_distance_A[2])
    conc_b_1_df = get_conc(att_b_1, optode_distance_B[0])
    conc_b_2_df = get_conc(att_b_2, optode_distance_B[1])
    conc_b_3_df = get_conc(att_b_3, optode_distance_B[2])

    # Convert attenuation arrays to DataFrames
    def att_to_df(att):
        return pd.DataFrame(att.T, columns=[f'{wl}' for wl in wavelengths])

    atten_a_1 = att_to_df(att_a_1)
    atten_a_2 = att_to_df(att_a_2)
    atten_a_3 = att_to_df(att_a_3)
    atten_b_1 = att_to_df(att_b_1)
    atten_b_2 = att_to_df(att_b_2)
    atten_b_3 = att_to_df(att_b_3)

    return (
        conc_a_1_df, conc_a_2_df, conc_a_3_df,
        conc_b_1_df, conc_b_2_df, conc_b_3_df,
        atten_a_1, atten_a_2, atten_a_3,
        atten_b_1, atten_b_2, atten_b_3, wavelengths
    )


import numpy as np
import pandas as pd

def SRS(data: pd.DataFrame):
    wavelengths = [782, 801, 808, 828, 848, 887]
    extinction_path = "src/concentrations_ucln_srs/defaults.csv"
    epsilon = pd.read_csv(extinction_path)

    n_samples = len(data)

    # Get attenuation data (shape: 6 wavelengths × samples × 3 detectors)
    def get_group_matrix(prefix):
        group_matrix = np.empty((6, n_samples, 3))
        for i, wl in enumerate(wavelengths):
            for d in range(1, 4):
                col = f'{prefix}_{wl}_DET{d}'
                group_matrix[i, :, d-1] = pd.to_numeric(data[col], errors='coerce').fillna(1e-10).values
        return group_matrix

    intensity_A = get_group_matrix("LED_A")
    intensity_B = get_group_matrix("LED_B")

    # Compute attenuation: log10(ref / intensity), ref=100
    attenuation_A = np.log10(100 / np.clip(intensity_A, 1e-10, None))
    attenuation_B = np.log10(100 / np.clip(intensity_B, 1e-10, None))

    # Optode distances in cm
    optode_distance_A = np.array([3, 4, 5]).reshape(-1, 1)
    optode_distance_B = np.array([5, 4, 3]).reshape(-1, 1)
    dets_a = [0, 1, 2]
    dets_b = [0, 1, 2]

    # Select attenuation for each detector
    atten_a = attenuation_A[:, :, dets_a]  # shape: (6, samples, 3)
    atten_b = attenuation_B[:, :, dets_b]

    # Slopes (m) for each wavelength and sample
    m_A_og = np.empty((6, n_samples))
    m_B_og = np.empty((6, n_samples))

    def get_slope(att, distances):
        att = att.flatten()
        distances = distances.flatten()
        A = np.vstack([distances, np.ones_like(distances)]).T
        return np.linalg.lstsq(A, att, rcond=None)[0][0]

    for l in range(6):
        for t in range(n_samples):
            m_A_og[l, t] = get_slope(atten_a[l, t, :], optode_distance_A)
            m_B_og[l, t] = get_slope(atten_b[l, t, :], optode_distance_B)

    # Compute k_mua
    h = 6.3e-4
    k_mua_A = np.empty((6, n_samples))
    k_mua_B = np.empty((6, n_samples))

    for l in range(6):
        h_corr = 1 - h * wavelengths[l]
        denominator = 3 * h_corr
        mean_A = np.mean(optode_distance_A)
        mean_B = np.mean(optode_distance_B)

        for t in range(n_samples):
            term_A = np.log(10) * m_A_og[l, t] - (2 / mean_A)
            term_B = np.log(10) * m_B_og[l, t] - (2 / mean_B)

            k_mua_A[l, t] = (1 / denominator) * (term_A ** 2)
            k_mua_B[l, t] = (1 / denominator) * (term_B ** 2)

    # Get extinction coefficients (HbO2, HHb) only
    ext_coeffs_srs = []
    for wl in wavelengths:
        row = epsilon[epsilon['wavelength'] == wl]
        if not row.empty:
            ext = row[['HbO2', 'HHb']].values.flatten()
            ext_coeffs_srs.append(ext)

    ext_coeffs_srs = np.array(ext_coeffs_srs)  # (6, 2)
    ext_inv = np.linalg.pinv(ext_coeffs_srs) * 10 / np.log(10)  # (2, 6)

    # Calculate concentrations
    kConc_A = ext_inv @ k_mua_A  # (2, n_samples)
    kConc_B = ext_inv @ k_mua_B

    # Extract HHb and HbO
    HHb_A, HbO_A = kConc_A[0, :], kConc_A[1, :]
    HHb_B, HbO_B = kConc_B[0, :], kConc_B[1, :]

    # Total hemoglobin
    HbT_A = HbO_A + HHb_A
    HbT_B = HbO_B + HHb_B

    # Calculate StO2
    sto2_A = (HbO_A / np.clip(HbT_A, 1e-10, None)) * 100
    sto2_B = (HbO_B / np.clip(HbT_B, 1e-10, None)) * 100

    return {
        'StO2_A': sto2_A,
        'StO2_B': sto2_B
    }
