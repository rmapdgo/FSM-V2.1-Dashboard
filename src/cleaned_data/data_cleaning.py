import os
import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt
import plotly.graph_objects as go
from dash import html, dcc

def subtract_dark(data, dark_mapping):
    for signal, dark in dark_mapping.items():
        if signal in data.columns and dark in data.columns:
            data[signal] = data[signal] - data[dark]
    return data

def apply_highpass_filter(data, cutoff, order, sr):
    b, a = butter(order, cutoff, btype='high', fs=sr)
    for col in data.select_dtypes(include='number').columns:
        data[col] = filtfilt(b, a, data[col].values)
    return data

def apply_lowpass_filter(data, cutoff, order, sr):
    b, a = butter(order, cutoff, btype='low', fs=sr)
    for col in data.select_dtypes(include='number').columns:
        data[col] = filtfilt(b, a, data[col].values)
    return data

def apply_bandpass_filter(data, lowcut, highcut, order, sr):
    b, a = butter(order, [lowcut, highcut], btype='bandpass', fs=sr)
    for col in data.select_dtypes(include='number').columns:
        data[col] = filtfilt(b, a, data[col].values)
    return data

def apply_median_filter(data, window_size):
    for col in data.select_dtypes(include='number').columns:
        data[col] = data[col].rolling(window=window_size, center=True).median()
    return data

def preprocess_and_plot(filepath, preprocessing_config, group_flags):
    original_data = pd.read_excel(filepath)
    data = original_data.copy()

    if preprocessing_config.get("subtract_dark"):
        data = subtract_dark(data, preprocessing_config["dark_mapping"])

    if preprocessing_config.get("highpass"):
        data = apply_highpass_filter(data, **preprocessing_config["highpass"])

    if preprocessing_config.get("lowpass"):
        data = apply_lowpass_filter(data, **preprocessing_config["lowpass"])

    if preprocessing_config.get("bandpass"):
        data = apply_bandpass_filter(data, **preprocessing_config["bandpass"])

    if preprocessing_config.get("median"):
        data = apply_median_filter(data, preprocessing_config["median"]["window_size"])

    os.makedirs("New_concentrations/src/cleaned_data/data_clean", exist_ok=True)
    output_path = "New_concentrations/src/cleaned_data/data_clean/cleaned_data.xlsx"
    data.to_excel(output_path, index=False)

    cleaned_data = pd.read_excel(output_path)

    grouped_columns = preprocessing_config["grouped_columns"]
    preprocessing_plots = []

    for group_name, columns in grouped_columns.items():
        if not group_flags.get(group_name):
            continue

        group_plots = []
        for col in columns:
            if col in cleaned_data.columns and col in original_data.columns:
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=original_data.index,
                    y=original_data[col],
                    mode='lines',
                    name=f"{col} - Original",
                    line=dict(dash='dash')
                ))

                fig.add_trace(go.Scatter(
                    x=cleaned_data.index,
                    y=cleaned_data[col],
                    mode='lines',
                    name=f"{col} - Processed",
                    line=dict(dash='solid')
                ))

                fig.update_layout(
                    title=f'Comparison for {col}',
                    title_font_size=20,
                    xaxis={'title': 'Time', 'title_font_size': 16, 'tickfont_size': 14},
                    yaxis={'title': 'Voltage', 'title_font_size': 16, 'tickfont_size': 14},
                    height=500
                )

                group_plots.append(html.Div(dcc.Graph(figure=fig), style={'padding': '15px'}))

        if group_plots:
            group_container = html.Div(
                children=[html.H3(group_name, style={'fontSize': '24px'}), *group_plots],
                style={'marginBottom': '30px'}
            )
            preprocessing_plots.append(group_container)

    return preprocessing_plots
