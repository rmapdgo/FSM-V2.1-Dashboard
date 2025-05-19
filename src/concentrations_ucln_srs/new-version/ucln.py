#==============================UCLN================================================================================
import pandas as pd
import numpy as np

# Load CSV, skipping the first 9 header lines
data = pd.read_csv('/home/darshana/Documents/FSM-V2.1/New_concentrations/src/uploads/1010081_28+5_20250515_V2.1_10.csv', skiprows=9)

# Wavelengths used (FSM2)
wavelengths = [782, 801, 808, 828, 848, 887]

# Get number of samples
n_samples = len(data['Abs system Time'])


epsilon_labview_770to906 = pd.read_csv('/home/darshana/Documents/FSM-V2.1/New_concentrations/src/concentrations_ucln_srs/defaults.csv', delimiter=',')

ext_coeffs = []
ext_coeffs_cor = []

for wl in wavelengths:
    row = epsilon_labview_770to906[epsilon_labview_770to906['wavelength'] == wl]
    if not row.empty:
        ext = row[['HbO2', 'HHb', 'CCO']].values.flatten()
        corr = row['wl_dep'].values[0]
        ext_coeffs.append(ext)
        ext_coeffs_cor.append(ext * corr)
    else:
        raise ValueError(f"Wavelength {wl} not found in extinction coefficient data.")

ext_coeffs = np.array(ext_coeffs)
ext_coeffs_cor = np.array(ext_coeffs_cor)

import numpy as np

# Pseudoinverse of corrected extinction coefficients
ext_coeffs_inv = np.linalg.pinv(ext_coeffs_cor)

# Convert to mm scale (assuming 10 / log(10) is a unit conversion)
ext_coeffs_mm = ext_coeffs_inv * 10 / np.log(10)

# Optode distances in mm
optode_distance_A = np.array([30, 40, 50]).reshape(-1, 1)  # Column vector
optode_distance_B = np.array([50, 40, 30]).reshape(-1, 1)  # Column vector

# Differential Pathlength Factor
DPF = 4.99

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

# Get number of samples
n_samples = len(data)

# Convert to numpy arrays with shape (samples, 6, 3)
intensity_A = data[intensity_A_columns].values.reshape(n_samples, 6, 3)
intensity_B = data[intensity_B_columns].values.reshape(n_samples, 6, 3)

print('intensity_A', intensity_A)
print('intensity_B', intensity_B)

import numpy as np

# Set reference intensity
ref_intensity = 100

# Initialize attenuation arrays with shape (6, samples, 3)
attenuation_A = np.empty((6, intensity_A.shape[0], 3))
attenuation_B = np.empty((6, intensity_B.shape[0], 3))

# Calculate attenuation: log10(ref_intensity / intensity)
for l in range(6):  # wavelengths
    for det in range(3):  # detectors
        attenuation_A[l, :, det] = np.log10(ref_intensity / intensity_A[:, l, det])
        attenuation_B[l, :, det] = np.log10(ref_intensity / intensity_B[:, l, det])

print('attenuation_A', attenuation_A)
print('attenuation_B', attenuation_B)

# attenuation_A, attenuation_B shape: (6, samples, 3)

delta_attenuation_A = attenuation_A[:, 0:1, :] - attenuation_A  # broadcasting over samples
delta_attenuation_B = attenuation_B[:, 0:1, :] - attenuation_B

print('delta_attenuation_A', delta_attenuation_A)
print('delta_attenuation_B', delta_attenuation_B)

concentration_A = []
concentration_B = []

# Corrected optode distances
opt_dist_A_corr = optode_distance_A.flatten() * DPF  # shape: (3,)
opt_dist_B_corr = optode_distance_B.flatten() * DPF

for det in range(3):
    delta_A = delta_attenuation_A[:, :, det] / opt_dist_A_corr[det]  # shape (6, samples)
    delta_B = delta_attenuation_B[:, :, det] / opt_dist_B_corr[det]  # shape (6, samples)

    conc_A = 10000 * ext_coeffs_inv @ delta_A  # shape (3, samples)
    conc_B = 10000 * ext_coeffs_inv @ delta_B  # shape (3, samples)

    concentration_A.append(conc_A)
    concentration_B.append(conc_B)

print('concentration_A', concentration_A)
print('concentration_B', concentration_B)

import matplotlib.pyplot as plt

chromophores = ['HHb', 'HbO₂', 'CCO']

# Convert to NumPy arrays before using .shape
concentration_A = np.array(concentration_A)  # (detectors=3, chromophores=3, samples)
concentration_B = np.array(concentration_B)

n_samples = concentration_A.shape[2]
time = np.arange(n_samples)  # or use actual time: data['Sample Time (s)'].values

# Plot concentration_A for each detector
for det in range(3):
    plt.figure(figsize=(12, 4))
    for chrom in range(3):
        plt.plot(time, concentration_A[det, chrom, :], label=f'{chromophores[chrom]}')
    plt.title(f'Concentration LED A - DET {det+1}')
    plt.xlabel('Sample Index')
    plt.ylabel('Concentration (µM)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# Plot concentration_B for each detector
for det in range(3):
    plt.figure(figsize=(12, 4))
    for chrom in range(3):
        plt.plot(time, concentration_B[det, chrom, :], label=f'{chromophores[chrom]}')
    plt.title(f'Concentration LED B - DET {det+1}')
    plt.xlabel('Sample Index')
    plt.ylabel('Concentration (µM)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


#================================SRS==============================================================================


# Optode distances in cm (shape: (3, 1))
optode_distance_A = np.array([3, 4, 5]).reshape(-1, 1)
optode_distance_B = np.array([5, 4, 3]).reshape(-1, 1)

# Select detectors (zero-based indexing in Python)
dets_a = [0, 1, 2]
dets_b = [0, 1, 2]

# Select distances (shape will be (3, 1))
optodes_A = optode_distance_A[dets_a]
optodes_B = optode_distance_B[dets_b]
print("Optodes A:", optodes_A.flatten())
print("Optodes B:", optodes_B.flatten())

# Select attenuation data (shape: (6, samples, 3))
atten_a = attenuation_A[:, :, dets_a]
atten_b = attenuation_B[:, :, dets_b]
print("Attenuation A shape:", atten_a.shape)
print("Attenuation B shape:", atten_b.shape)

# Number of samples
n_samples = attenuation_A.shape[1]
print("Number of samples:", n_samples)

# Step 1: Calculate slope matrix
m_A_og = np.empty((6, n_samples))
m_B_og = np.empty((6, n_samples))

def get_slopes(att, distances):
    att = att.flatten()
    distances = distances.flatten()
    A = np.vstack([distances, np.ones_like(distances)]).T
    slope = np.linalg.lstsq(A, att, rcond=None)[0][0]
    return slope

for l in range(6):
    for t in range(n_samples):
        m_A_og[l, t] = get_slopes(atten_a[l, t, :], optodes_A)
        m_B_og[l, t] = get_slopes(atten_b[l, t, :], optodes_B)

print("Slope matrix A (m_A_og):", m_A_og)
print("Slope matrix B (m_B_og):", m_B_og)

# Step 2: Calculate k_mua
h = 6.3e-4
k_mua_A = np.empty((6, n_samples))
k_mua_B = np.empty((6, n_samples))
h_calc = np.empty(6)

for l in range(6):
    h_calc[l] = 1 - h * wavelengths[l]
    denominator = 3 * h_calc[l]
    mean_A = np.mean(optodes_A)
    mean_B = np.mean(optodes_B)

    for t in range(n_samples):
        term_A = np.log(10) * m_A_og[l, t] - (2 / mean_A)
        term_B = np.log(10) * m_B_og[l, t] - (2 / mean_B)

        k_mua_A[l, t] = (1 / denominator) * (term_A ** 2)
        k_mua_B[l, t] = (1 / denominator) * (term_B ** 2)

print("k_mua_A:", k_mua_A)
print("k_mua_B:", k_mua_B)

# Step 3: Get extinction coefficients
ext_coeffs_srs = []
wldep = []

for wl in wavelengths:
    row = epsilon_labview_770to906[epsilon_labview_770to906['wavelength'] == wl]
    if not row.empty:
        ext = row[['HbO2', 'HHb']].values.flatten()
        corr = row['wl_dep'].values[0]
        ext_coeffs_srs.append(ext)
        wldep.append(corr)

ext_coeffs_srs = np.array(ext_coeffs_srs)
wldep = np.array(wldep)
print("Extinction coefficients (HbO2, HHb):", ext_coeffs_srs)
print("Wavelength dependent correction:", wldep)

# Step 4: Inverse extinction matrix
ext_coeffs_srs_inv = np.linalg.pinv(ext_coeffs_srs)
ext_coeffs_srs_mm = ext_coeffs_srs_inv * 10 / np.log(10)
print("Inverse extinction matrix (mm):", ext_coeffs_srs_mm)

# Step 5: Apply to get concentrations
kConc_A = ext_coeffs_srs_mm @ k_mua_A
kConc_B = ext_coeffs_srs_mm @ k_mua_B

print("kConc_A (HbO2 row, HHb row):", kConc_A)
print("kConc_B (HbO2 row, HHb row):", kConc_B)

# Step 6: Extract values
kHHb_A = kConc_A[0, :]
kHbO_A = kConc_A[1, :]
kHbT_A = kHbO_A + kHHb_A

kHHb_B = kConc_B[0, :]
kHbO_B = kConc_B[1, :]
kHbT_B = kHbO_B + kHHb_B

print("kHHb_A:", kHHb_A)
print("kHbO_A:", kHbO_A)
print("kHbT_A:", kHbT_A)
print("kHHb_B:", kHHb_B)
print("kHbO_B:", kHbO_B)
print("kHbT_B:", kHbT_B)

# Step 7: Compute StO2
sto2_A = (kHbO_A / kHbT_A) * 100
sto2_B = (kHbO_B / kHbT_B) * 100

print("StO2_A (%):", sto2_A)
print("StO2_B (%):", sto2_B)


import matplotlib.pyplot as plt

# Time axis (use actual time if available)
time = np.arange(n_samples)  # or: data['Sample Time (s)'].values

# Plot sto2_A
plt.figure(figsize=(12, 4))
plt.plot(time, sto2_A, label='StO₂ A', color='blue')
plt.title('StO₂ - LED A')
plt.xlabel('Sample Index')
plt.ylabel('StO₂ (%)')
plt.ylim(0, 100)
plt.grid(True)
plt.tight_layout()
plt.legend()
plt.show()

# Plot sto2_B
plt.figure(figsize=(12, 4))
plt.plot(time, sto2_B, label='StO₂ B', color='green')
plt.title('StO₂ - LED B')
plt.xlabel('Sample Index')
plt.ylabel('StO₂ (%)')
plt.ylim(0, 100)
plt.grid(True)
plt.tight_layout()
plt.legend()
plt.show()

# Path to save the CSV
save_path = "/home/darshana/Documents/FSM-V2.1-dashboard/New layout/src/concentrations_ucln_srs/concentration_data.csv"

# Create DataFrame
concentration_data = pd.DataFrame({
    'Time_Index': time,
    'UCLN_HHb_A_DET1': concentration_A[0, 0, :],
    'UCLN_HbO_A_DET1': concentration_A[0, 1, :],
    'UCLN_CCO_A_DET1': concentration_A[0, 2, :],
    'UCLN_HHb_B_DET1': concentration_B[0, 0, :],
    'UCLN_HbO_B_DET1': concentration_B[0, 1, :],
    'UCLN_CCO_B_DET1': concentration_B[0, 2, :],
    'SRS_StO2_A': sto2_A,
    'SRS_StO2_B': sto2_B
})

# Save to CSV
concentration_data.to_csv(save_path, index=False)
print(f"Saved concentration and StO₂ data to: {save_path}")
