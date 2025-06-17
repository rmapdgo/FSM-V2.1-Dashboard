import numpy as np
import pandas as pd

def dual_slope_wavelength(data: pd.DataFrame):
    print("[DualSlope] Starting calculation...")
    epsilon_path = 'src/concentrations_ucln_srs/defaults.csv'
    wavelengths = [782, 801, 808, 828, 848, 887]
    n_samples = len(data)
    print(f"[DualSlope] Number of samples: {n_samples}")

    # Load extinction coefficients
    print("[DualSlope] Loading extinction coefficients...")
    epsilon = pd.read_csv(epsilon_path)
    ext_coeffs = []
    for wl in wavelengths:
        row = epsilon[epsilon['wavelength'] == wl]
        if not row.empty:
            coeffs = row[['HbO2', 'HHb']].values.flatten()
            ext_coeffs.append(coeffs)
            print(f"[DualSlope] Loaded extinction coeffs for wavelength {wl}: {coeffs}")
        else:
            raise ValueError(f"Wavelength {wl} not found in extinction data.")

    ext_coeffs = np.array(ext_coeffs)  # shape (6, 2)
    print(f"[DualSlope] Extinction coefficients shape: {ext_coeffs.shape}")

    # Compute pseudoinverse and scale
    ext_coeffs_inv = np.linalg.pinv(ext_coeffs)
    ext_coeffs_mm = ext_coeffs_inv * 10 / np.log(10)  # shape: (2, 6)
    print(f"[DualSlope] Pseudoinverse shape: {ext_coeffs_inv.shape}")

    # Extract intensity columns and reshape
    intensity_A_columns = [f'LED_A_{wl}_DET{i}' for wl in wavelengths for i in [1, 2, 3]]
    intensity_B_columns = [f'LED_B_{wl}_DET{i}' for wl in wavelengths for i in [1, 2, 3]]

    print("[DualSlope] Extracting intensity data from dataframe...")
    intensity_A = data[intensity_A_columns].values.reshape(n_samples, 6, 3)
    intensity_B = data[intensity_B_columns].values.reshape(n_samples, 6, 3)
    print(f"[DualSlope] Intensity_A shape: {intensity_A.shape}, Intensity_B shape: {intensity_B.shape}")

    distances = np.array([30, 40, 50])  # distances in mm or cm

    def vectorized_dual_slope_eq18(intensities, distances):
        # intensities: shape (n_samples, N)
        distances = np.array(distances)
        N = len(distances)
        r_mean = np.mean(distances)
        r_var = np.var(distances)
    
        # Compute log term for all samples and all distances
        val = (distances ** 2)[None, :] * intensities  # broadcasting distances^2 * intensities
    
        # Avoid log of zero or negative by clipping
        val = np.clip(val, a_min=np.finfo(float).eps, a_max=None)
        log_term = np.log(val)  # shape (n_samples, N)
    
        deviations = distances - r_mean  # shape (N,)
    
        numerator = np.sum(log_term * deviations[None, :], axis=1)  # shape (n_samples,)
        slope = numerator / (N * r_var)
        return slope


    print("[DualSlope] Computing slopes for each wavelength and sample...")
    eq18_slope_A = np.empty((6, n_samples))
    eq18_slope_B = np.empty((6, n_samples))

    for lam in range(6):
        print(f"[DualSlope] Processing wavelength index {lam + 1}/6...")

        # For A
        I_A = intensity_A[:, lam, :]  # shape (n_samples, 3)
        eq18_slope_A[lam, :] = vectorized_dual_slope_eq18(I_A, distances)

        # For B (reversed)
        I_B = intensity_B[:, lam, ::-1]  # shape (n_samples, 3)
        eq18_slope_B[lam, :] = vectorized_dual_slope_eq18(I_B, distances)

    print("[DualSlope] Finished computing slopes.")

    # Apply factor 6.9
    mua_A = -eq18_slope_A / 6.9
    mua_B = -eq18_slope_B / 6.9

    selected_lambdas = [0, 1, 2, 3, 4, 5]  # all six wavelengths
    mua_A_selected = mua_A[selected_lambdas, :]
    mua_B_selected = mua_B[selected_lambdas, :]

    print("[DualSlope] Calculating concentrations from absorption coefficients...")
    conc_A = ext_coeffs_mm @ mua_A_selected
    conc_B = ext_coeffs_mm @ mua_B_selected

    # Compute StO2
    HbO2_A = conc_A[1]
    HHb_A = conc_A[0]
    sto2_A = (HbO2_A / (HbO2_A + HHb_A)) * 100

    HbO2_B = conc_B[1]
    HHb_B = conc_B[0]
    sto2_B = (HbO2_B / (HbO2_B + HHb_B)) * 100

    # Average MUA and compute final concentrations and StO2
    mua_AB_selected = (mua_A_selected + mua_B_selected) / 2
    conc_AB = ext_coeffs_mm @ mua_AB_selected

    HbO2_AB = conc_AB[1]
    HHb_AB = conc_AB[0]
    sto2_AB = (HbO2_AB / (HbO2_AB + HHb_AB)) * 100

    # Clamp negative values to zero
    sto2_AB = np.maximum(0, sto2_AB)

    print("[DualSlope] Dual slope StO2 calculation complete.")

    return {
        "ds_sto2_AB": sto2_AB,
        "ds_sto2_A": sto2_A,
        "ds_sto2_B": sto2_B,
    }
