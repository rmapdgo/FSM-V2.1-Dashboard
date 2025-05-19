import numpy as np
import pandas as pd
import plotly.graph_objects as go

def data_quality_check(data, selected_dropdown):
    # Define the signal-dark dictionary (remains unchanged)
    signal_dark_dictionary = {
        # Group A
        'LED_A_782_DET1': 'LED_A_DARK_DET1', 'LED_A_801_DET1': 'LED_A_DARK_DET1', 'LED_A_808_DET1': 'LED_A_DARK_DET1',
        'LED_A_828_DET1': 'LED_A_DARK_DET1', 'LED_A_848_DET1': 'LED_A_DARK_DET1', 'LED_A_887_DET1': 'LED_A_DARK_DET1',
        'LED_A_782_DET2': 'LED_A_DARK_DET2', 'LED_A_801_DET2': 'LED_A_DARK_DET2', 'LED_A_808_DET2': 'LED_A_DARK_DET2',
        'LED_A_828_DET2': 'LED_A_DARK_DET2', 'LED_A_848_DET2': 'LED_A_DARK_DET2', 'LED_A_887_DET2': 'LED_A_DARK_DET2',
        'LED_A_782_DET3': 'LED_A_DARK_DET3', 'LED_A_801_DET3': 'LED_A_DARK_DET3', 'LED_A_808_DET3': 'LED_A_DARK_DET3',
        'LED_A_828_DET3': 'LED_A_DARK_DET3', 'LED_A_848_DET3': 'LED_A_DARK_DET3', 'LED_A_887_DET3': 'LED_A_DARK_DET3',
        
        # Group B
        'LED_B_782_DET1': 'LED_B_DARK_DET1', 'LED_B_801_DET1': 'LED_B_DARK_DET1', 'LED_B_808_DET1': 'LED_B_DARK_DET1',
        'LED_B_828_DET1': 'LED_B_DARK_DET1', 'LED_B_848_DET1': 'LED_B_DARK_DET1', 'LED_B_887_DET1': 'LED_B_DARK_DET1',
        'LED_B_782_DET2': 'LED_B_DARK_DET2', 'LED_B_801_DET2': 'LED_B_DARK_DET2', 'LED_B_808_DET2': 'LED_B_DARK_DET2',
        'LED_B_828_DET2': 'LED_B_DARK_DET2', 'LED_B_848_DET2': 'LED_B_DARK_DET2', 'LED_B_887_DET2': 'LED_B_DARK_DET2',
        'LED_B_782_DET3': 'LED_B_DARK_DET3', 'LED_B_801_DET3': 'LED_B_DARK_DET3', 'LED_B_808_DET3': 'LED_B_DARK_DET3',
        'LED_B_828_DET3': 'LED_B_DARK_DET3', 'LED_B_848_DET3': 'LED_B_DARK_DET3', 'LED_B_887_DET3': 'LED_B_DARK_DET3'
    }

    # Function to calculate SNR (remains unchanged)
    def calculate_snr(signal_data, dark_data):
        signal = np.mean(signal_data)
        dark_mean = np.mean(dark_data)
        snr = (signal - dark_mean) / dark_mean
        return snr

    # Initialize an empty dictionary to store the SNR values
    snr_dict = {}

    # Loop over each entry in the signal-dark dictionary and calculate SNR for each pair
    for signal_col in signal_dark_dictionary:
        dark_col = signal_dark_dictionary[signal_col]
        snr_value = calculate_snr(data[signal_col], data[dark_col])
        snr_dict[signal_col] = snr_value

    # Convert SNR values into lists for plotting
    snr_values = list(snr_dict.values())  
    snr_keys = list(snr_dict.keys())

    # Create the SNR histogram with title
    snr_hist_fig = go.Figure(data=[go.Bar(x=snr_keys, y=snr_values)])
    snr_hist_fig.update_layout(
        title="SNR Histogram of All LED Detectors",
        xaxis_title="LED Detectors",
        yaxis_title="SNR",
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin={'l': 60, 'r': 40, 't': 80, 'b': 60},
        height=600
    )

    # Retrieve the SNR for the selected dropdown value
    snr_value = snr_dict.get(selected_dropdown, 0)  # Default to 0 if the selected item is not in the dictionary

    # Create the SNR gauge chart (indicator) for the selected dropdown value with title
    snr_plot = go.Figure(go.Indicator(
        mode="gauge+number",
        value=snr_value,
        title={'text': f"SNR of {selected_dropdown}"},
        gauge={
            'axis': {'range': [None, 10]},  # Adjust the max range as needed
            'bar': {'color': "blue"},
            'steps': [
                {'range': [0, 1], 'color': "red"},
                {'range': [1, 2], 'color': "yellow"},
                {'range': [2, 10], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': snr_value
            }
        }
    ))

    # Group SNR Calculation (based on the three groups defined in the original code)
    def calculate_group_snr(group):
        snr_values = []
        for signal_col in group:
            dark_col = signal_dark_dictionary.get(signal_col)  # Get corresponding dark column
            if dark_col:
                snr_value = calculate_snr(data[signal_col], data[dark_col])
                snr_values.append(snr_value)
        return np.mean(snr_values) if snr_values else 0  # Return 0 if no SNR values are calculated
    
    # Function to calculate NEP (standard deviation of dark signal)
    def calculate_nep(group_dark_columns):
        dark_data = []
        for dark_col in group_dark_columns:
            dark_data.append(data[dark_col])  # Add the dark column data
        # Stack the dark data and calculate the standard deviation (NEP)
        combined_dark_data = np.concatenate(dark_data, axis=0)
        nep_value = np.std(combined_dark_data)
        return nep_value

    group_1_snr = calculate_group_snr([
        'LED_A_782_DET1', 'LED_A_801_DET1', 'LED_A_808_DET1', 'LED_A_828_DET1', 'LED_A_848_DET1', 'LED_A_887_DET1',
        'LED_B_782_DET3', 'LED_B_801_DET3', 'LED_B_808_DET3', 'LED_B_828_DET3', 'LED_B_848_DET3', 'LED_B_887_DET3'
    ])
    
    group_2_snr = calculate_group_snr([
        'LED_A_782_DET2', 'LED_A_801_DET2', 'LED_A_808_DET2', 'LED_A_828_DET2', 'LED_A_848_DET2', 'LED_A_887_DET2',
        'LED_B_782_DET2', 'LED_B_801_DET2', 'LED_B_808_DET2', 'LED_B_828_DET2', 'LED_B_848_DET2', 'LED_B_887_DET2'
    ])
    
    group_3_snr = calculate_group_snr([
        'LED_A_782_DET3', 'LED_A_801_DET3', 'LED_A_808_DET3', 'LED_A_828_DET3', 'LED_A_848_DET3', 'LED_A_887_DET3',
        'LED_B_782_DET1', 'LED_B_801_DET1', 'LED_B_808_DET1', 'LED_B_828_DET1', 'LED_B_848_DET1', 'LED_B_887_DET1'
    ])
    # Calculate NEP for each group
    group_1_nep = calculate_nep([
        'LED_A_DARK_DET1', 'LED_B_DARK_DET1'
    ])

    group_2_nep = calculate_nep([
        'LED_A_DARK_DET2', 'LED_B_DARK_DET2'
    ])

    group_3_nep = calculate_nep([
        'LED_A_DARK_DET3', 'LED_B_DARK_DET3'
    ])

    # Create the bar chart for the average SNR of each group
    snr_bar_chart = go.Figure(data=[go.Bar(
        x=['LED_A_Detector_1 + LED_B_Detector_3', 'LED_A_Detector_2 + LED_B_Detector_2', 'LED_A_Detector_3 + LED_B_Detector_1'],
        y=[group_1_snr, group_2_snr, group_3_snr],
        name='Average SNR',
        marker_color='rgba(0, 123, 255, 0.6)',  # Blue color
        text=[f"{group_1_snr:.2f}", f"{group_2_snr:.2f}", f"{group_3_snr:.2f}"],  # Add text with the average SNR values
        textposition="outside"
    )])

    snr_bar_chart.update_layout(
        title="Average SNR of Each Group",
        xaxis_title="Group",
        yaxis_title="Average SNR",
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin={'l': 60, 'r': 40, 't': 80, 'b': 60},
        height=600
    )

    # Create the bar chart for the NEP of each group
    nep_bar_chart = go.Figure(data=[go.Bar(
        x=['LED_A_Dark_DET1 + LED_B_Dark_DET1', 'LED_A_Dark_DET2 + LED_B_Dark_DET2', 'LED_A_Dark_DET3 + LED_B_Dark_DET3'],
        y=[group_1_nep, group_2_nep, group_3_nep],
        name='NEP',
        marker_color='rgba(255, 99, 132, 0.6)',  # Red color
        text=[f"{group_1_nep}", f"{group_2_nep}", f"{group_3_nep}"],  # Add text with the average NEP values
        textposition="outside"
    )])

    nep_bar_chart.update_layout(
        title="NEP (Standard Deviation of Dark) for Each Group",
        xaxis_title="Group",
        yaxis_title="NEP (Standard Deviation)",
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin={'l': 60, 'r': 40, 't': 80, 'b': 60},
        height=600
    )

    # Create scatter plot for the selected dropdown with time on x-axis and signal data on y-axis
    scatter_plot = go.Figure(data=go.Scatter(
    x = data['Time'] if 'Time' in data.columns else data['total_seconds'],
    y=data[selected_dropdown],  # Signal data from the selected dropdown
    mode='markers',
    marker=dict(color='blue', size=8)
    ))

    scatter_plot.update_layout(
    title=f"Scatter Plot for {selected_dropdown}",
    xaxis_title="Time",
    yaxis_title="Signal",
    plot_bgcolor='white',
    paper_bgcolor='white',
    margin={'l': 60, 'r': 40, 't': 80, 'b': 60},
    height=600
    )


    # Distance to Dark Calculation
    distance_to_dark_values = {}

    # Loop over each signal-dark pair to calculate the distance to dark
    for signal_col in signal_dark_dictionary:
        dark_col = signal_dark_dictionary[signal_col]
        signal_data = data[signal_col].dropna()  # Signal data
        dark_data = data[dark_col].dropna()  # Dark data

        # Ensure both series have the same length before calculating distance
        min_length = min(len(signal_data), len(dark_data))

        if min_length > 0:
            distance = np.linalg.norm(signal_data.iloc[:min_length].values - dark_data.iloc[:min_length].values)
            distance_to_dark_values[signal_col] = distance
        else:
            distance_to_dark_values[signal_col] = np.nan

    # Filter out NaN values
    distance_to_dark_values = {k: v for k, v in distance_to_dark_values.items() if not np.isnan(v)}

    # Create a line plot with markers for Distance to Dark
    distance_to_dark_plot = go.Figure(data=[
        go.Scatter(
            x=list(distance_to_dark_values.keys()),
            y=list(distance_to_dark_values.values()),
            mode='lines+markers',
            marker=dict(color='blue', size=10),
            line=dict(color='blue', width=2)
        )
    ])

    # Update layout for the Distance to Dark plot
    distance_to_dark_plot.update_layout(
        title="Distance to Dark Spectra",
        xaxis_title="Signal Columns",
        yaxis_title="Distance to Dark",
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin={'l': 60, 'r': 40, 't': 80, 'b': 60},
        height=600
    )

    # Return all the figures
    return snr_hist_fig, snr_plot, snr_bar_chart, nep_bar_chart, scatter_plot, distance_to_dark_plot

