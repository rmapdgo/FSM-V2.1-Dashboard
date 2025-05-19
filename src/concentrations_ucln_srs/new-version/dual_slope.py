import pandas as pd
import numpy as np

# Load CSV, skipping the first 9 header lines
data = pd.read_csv('/home/darshana/Documents/FSM-V2.1-dashboard/New layout/src/uploads/PROT2_fsm_data_15_38_38.207976 1.csv', skiprows=9)

# Wavelengths used (FSM2)
wavelengths = [782, 801, 808, 828, 848, 887]

# Get number of samples
n_samples = len(data['Abs system Time'])

epsilon_labview_770to906 = pd.read_csv('New layout/src/concentrations_ucln_srs/defaults.csv', delimiter=',')

ext_coeffs_srs = []
wldep = []

for wl in wavelengths:
    # Filter row for current wavelength
    row = epsilon_labview_770to906[epsilon_labview_770to906['wavelength'] == wl]
    if not row.empty:
        # Extract HbO2 and HHb
        ext_coeffs_srs.append(row[['HbO2', 'HHb']].values.flatten())
        # Extract wl_dep
        wldep.append(row['wl_dep'].values[0])
    else:
        raise ValueError(f"Wavelength {wl} not found in extinction data.")
        
# Convert lists to numpy arrays
ext_coeffs_srs = np.array(ext_coeffs_srs)  # Shape: (6, 2)
wldep = np.array(wldep)  # Shape: (6,)

import numpy as np

# Pseudoinverse
ext_coeffs_srs_inv = np.linalg.pinv(ext_coeffs_srs)  # shape: (2, 6)
ext_coeffs_srs_mm = ext_coeffs_srs_inv * 10 / np.log(10)  # scale factor

# Optode distances (column vectors)
optode_distance_A = np.array([[30], [40], [50]])  # shape: (3,1)
optode_distance_B = np.array([[50], [40], [30]])  # shape: (3,1)

# Define the list of column names manually for each
intensity_A_columns = [
    'Array A W1 PD1', 'Array A W1 PD2', 'Array A W1 PD3',
    'Array A W2 PD1', 'Array A W2 PD2', 'Array A W2 PD3',
    'Array A W3 PD1', 'Array A W3 PD2', 'Array A W3 PD3',
    'Array A W4 PD1', 'Array A W4 PD2', 'Array A W4 PD3',
    'Array A W5 PD1', 'Array A W5 PD2', 'Array A W5 PD3',
    'Array A W6 PD1', 'Array A W6 PD2', 'Array A W6 PD3'
]

intensity_B_columns = [
    'Array B W1 PD1', 'Array B W1 PD2', 'Array B W1 PD3',
    'Array B W2 PD1', 'Array B W2 PD2', 'Array B W2 PD3',
    'Array B W3 PD1', 'Array B W3 PD2', 'Array B W3 PD3',
    'Array B W4 PD1', 'Array B W4 PD2', 'Array B W4 PD3',
    'Array B W5 PD1', 'Array B W5 PD2', 'Array B W5 PD3',
    'Array B W6 PD1', 'Array B W6 PD2', 'Array B W6 PD3'
]

# Convert to numpy arrays with shape (samples, 6, 3)
intensity_A = data[intensity_A_columns].values.reshape(n_samples, 6, 3)
intensity_B = data[intensity_B_columns].values.reshape(n_samples, 6, 3)


# Initialize output arrays
eq18_slope_A = np.empty((6, n_samples))
eq18_slope_B = np.empty((6, n_samples))
decrease_A = np.empty((6, n_samples))
decrease_B = np.empty((6, n_samples))
eq_18_mua_A = np.empty((6, n_samples))
eq_18_mua_B = np.empty((6, n_samples))

def dual_slope_eq18(intensities, distances):
    intensities = np.array(intensities, dtype=float)
    distances = np.array(distances, dtype=float)
    log_intensities = np.log(intensities)
    A = np.vstack([distances, np.ones_like(distances)]).T
    slope, intercept = np.linalg.lstsq(A, log_intensities, rcond=None)[0]
    return slope, slope  # Both outputs are slope, for compatibility with MATLAB


# Loop over wavelengths and samples
for lam in range(6):  # 0-based in Python
    for t in range(n_samples):
        # Detector intensities: A in order, B in reverse
        intensities_A = [
            intensity_A[t, lam, 0],
            intensity_A[t, lam, 1],
            intensity_A[t, lam, 2],
        ]

        intensities_B = [
            intensity_B[t, lam, 2],
            intensity_B[t, lam, 1],
            intensity_B[t, lam, 0],
        ]

        distances = [3, 4, 5]

        # Apply dual slope function
        eq18_slope_A[lam, t], decrease_A[lam, t] = dual_slope_eq18(intensities_A, distances)
        eq18_slope_B[lam, t], decrease_B[lam, t] = dual_slope_eq18(intensities_B, distances)

        # Calculate mua
        eq_18_mua_A[lam, t] = -eq18_slope_A[lam, t] / 6.9
        eq_18_mua_B[lam, t] = -eq18_slope_B[lam, t] / 6.9

# Select all 6 wavelengths (Python is 0-based, MATLAB 1-based)
selected_lambdas = [0, 1, 2, 3, 4, 5]

# Calculate concentrations for A and B
conc_A = ext_coeffs_srs_mm @ eq_18_mua_A[selected_lambdas, :]  # shape: (2, n_samples)
conc_B = ext_coeffs_srs_mm @ eq_18_mua_B[selected_lambdas, :]

# Extract HbO and HHb (HbO = 2nd row, HHb = 1st row)
hbo_A = conc_A[1, :]
hhb_A = conc_A[0, :]
sto2_A = (hbo_A / (hbo_A + hhb_A)) * 100

hbo_B = conc_B[1, :]
hhb_B = conc_B[0, :]
sto2_B = (hbo_B / (hbo_B + hhb_B)) * 100

# Average mua from A and B
eq_18_mua_AB = (eq_18_mua_A + eq_18_mua_B) / 2

# Compute average concentration and StO₂
ds_conc_AB = ext_coeffs_srs_mm @ eq_18_mua_AB[selected_lambdas, :]

hbo_AB = ds_conc_AB[1, :]
hhb_AB = ds_conc_AB[0, :]
ds_sto2_AB = (hbo_AB / (hbo_AB + hhb_AB)) * 100

# Count how many values are out of bounds
num_above_100_DS = np.sum(ds_sto2_AB > 100)
num_below_0_DS = np.sum(ds_sto2_AB < 0)

total_corrections_DS = num_above_100_DS + num_below_0_DS
perc_correction_DS = (total_corrections_DS / n_samples) * 100

# Clamp values between 0 and 100
ds_sto2_AB = np.clip(ds_sto2_AB, 0, 100)

import matplotlib.pyplot as plt
import numpy as np

# Time axis (sample index or real time if available)
time = np.arange(n_samples)  # or use: data['Sample Time (s)'].values

# Plotting
plt.figure(figsize=(12, 4))
plt.plot(time, ds_sto2_AB, label='Dual-Slope StO₂ (A+B Avg)', color='purple')
plt.title('Dual-Slope StO₂ (Averaged from LED A and B)')
plt.xlabel('Sample Index')
plt.ylabel('StO₂ (%)')
plt.ylim(0, 100)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
