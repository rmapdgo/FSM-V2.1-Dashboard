import numpy as np
import pandas as pd

def dual_slope_wavelength(data: pd.DataFrame):
    epsilon_path='src/concentrations_ucln_srs/defaults.csv'
    wavelengths = [782, 801, 808, 828, 848, 887]
    n_samples = len(data)

    # Load extinction coefficients
    epsilon = pd.read_csv(epsilon_path)

    ext_coeffs_srs = []
    for wl in wavelengths:
        row = epsilon[epsilon['wavelength'] == wl]
        if not row.empty:
            ext_coeffs_srs.append(row[['HbO2', 'HHb']].values.flatten())
        else:
            raise ValueError(f"Wavelength {wl} not found in extinction data.")

    ext_coeffs_srs = np.array(ext_coeffs_srs)  # (6, 2)
    ext_coeffs_srs_inv = np.linalg.pinv(ext_coeffs_srs)  # (2, 6)
    ext_coeffs_srs_mm = ext_coeffs_srs_inv * 10 / np.log(10)

    # Define the list of column names manually for each
    intensity_A_columns = [
    'LED_A_782_DET1', 'LED_A_782_DET2', 'LED_A_782_DET3',
    'LED_A_801_DET1', 'LED_A_801_DET2', 'LED_A_801_DET3', 'LED_A_808_DET1', 'LED_A_808_DET2', 'LED_A_808_DET3',
    'LED_A_828_DET1', 'LED_A_828_DET2', 'LED_A_828_DET3', 'LED_A_848_DET1', 'LED_A_848_DET2', 'LED_A_848_DET3',
    'LED_A_887_DET1', 'LED_A_887_DET2', 'LED_A_887_DET3', 
    ]

    intensity_B_columns = ['LED_B_782_DET1', 'LED_B_782_DET2', 'LED_B_782_DET3', 'LED_B_801_DET1', 'LED_B_801_DET2', 'LED_B_801_DET3',
    'LED_B_808_DET1', 'LED_B_808_DET2', 'LED_B_808_DET3', 'LED_B_828_DET1', 'LED_B_828_DET2', 'LED_B_828_DET3',
    'LED_B_848_DET1', 'LED_B_848_DET2', 'LED_B_848_DET3', 'LED_B_887_DET1', 'LED_B_887_DET2', 'LED_B_887_DET3',
    ]

    # Reshape to (samples, 6, 3)
    intensity_A = data[intensity_A_columns].values.reshape(n_samples, 6, 3)
    intensity_B = data[intensity_B_columns].values.reshape(n_samples, 6, 3)

    eq18_slope_A = np.empty((6, n_samples))
    eq18_slope_B = np.empty((6, n_samples))
    eq_18_mua_A = np.empty((6, n_samples))
    eq_18_mua_B = np.empty((6, n_samples))

    def dual_slope_eq18(intensities, distances):
        log_intensities = np.log(intensities)
        A = np.vstack([distances, np.ones_like(distances)]).T
        slope, _ = np.linalg.lstsq(A, log_intensities, rcond=None)[0]
        return slope, slope  # For compatibility

    distances = [3, 4, 5]

    for lam in range(6):
        for t in range(n_samples):
            intensities_A = intensity_A[t, lam, :]
            intensities_B = intensity_B[t, lam, ::-1]  # reverse order

            eq18_slope_A[lam, t], _ = dual_slope_eq18(intensities_A, distances)
            eq18_slope_B[lam, t], _ = dual_slope_eq18(intensities_B, distances)

            eq_18_mua_A[lam, t] = -eq18_slope_A[lam, t] / 6.9
            eq_18_mua_B[lam, t] = -eq18_slope_B[lam, t] / 6.9

    selected_lambdas = [0, 1, 2, 3, 4, 5]

    # Compute concentrations
    conc_A = ext_coeffs_srs_mm @ eq_18_mua_A[selected_lambdas, :]
    conc_B = ext_coeffs_srs_mm @ eq_18_mua_B[selected_lambdas, :]

    hbo_A = conc_A[1, :]
    hhb_A = conc_A[0, :]
    sto2_A = (hbo_A / (hbo_A + hhb_A)) * 100

    hbo_B = conc_B[1, :]
    hhb_B = conc_B[0, :]
    sto2_B = (hbo_B / (hbo_B + hhb_B)) * 100

    # Average mua
    eq_18_mua_AB = (eq_18_mua_A + eq_18_mua_B) / 2
    ds_conc_AB = ext_coeffs_srs_mm @ eq_18_mua_AB[selected_lambdas, :]

    hbo_AB = ds_conc_AB[1, :]
    hhb_AB = ds_conc_AB[0, :]
    ds_sto2_AB = (hbo_AB / (hbo_AB + hhb_AB)) * 100

    # Clamp values
    num_above_100 = np.sum(ds_sto2_AB > 100)
    num_below_0 = np.sum(ds_sto2_AB < 0)
    total_corrections = num_above_100 + num_below_0
    perc_correction = (total_corrections / n_samples) * 100

    ds_sto2_AB = np.clip(ds_sto2_AB, 0, 100)

    return {"ds_sto2_AB": ds_sto2_AB}


