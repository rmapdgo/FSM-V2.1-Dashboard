import dash
from dash import Dash, dcc, html, Input, Output, State, callback, ctx
import boto3
import base64
import io
import openpyxl
import dash_daq as daq
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import glob
from src.snirf.create_snirf import create_snirf
from src.data_quality_check.data_quality_check import data_quality_check
import numpy as np
from src.concentrations_ucln_srs.ucln_srs import UCLN, SRS
from src.concentrations_ucln_srs.dualSlope import dual_slope_wavelength
import plotly.express as px
import flask
import plotly.graph_objects as go
import os
from openpyxl.utils.dataframe import dataframe_to_rows
import plotly.express as px
import dash_core_components as dcc
import dash_html_components as html
import logging
import os
from scipy.signal import butter, filtfilt, medfilt
import numpy as np
import pandas as pd
from dash import callback_context
from dash import html, callback_context
import base64
from dash.exceptions import PreventUpdate
import xlsxwriter
from openpyxl.utils.dataframe import dataframe_to_rows
from dash import no_update


# Create the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# AWS S3 client setup
s3 = boto3.client('s3',
    aws_access_key_id='AKIAT64DSU55EBYQBKGM',
    aws_secret_access_key='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'
)

# Bucket mapping
bucket_map = {
    'upload-raw': 'fsm-v2.1-raw-intensity-data',
    'upload-concentration': 'fsm-v2.1-concentrations-data',
    'upload-ctg': 'fsm-v2.1-ctg-data'
}

# Upload modal component
def get_upload_modal():
    return html.Div(
        id='upload-modal',
        style={
            'display': 'none',
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'width': '100%',
            'height': '100%',
            'backgroundColor': 'rgba(0, 0, 0, 0.6)',
            'zIndex': '1000',
            'display': 'flex',
            'justifyContent': 'center',
            'alignItems': 'center',
            'backdropFilter': 'blur(4px)'
        },
        children=html.Div(
            style={
                'background': 'linear-gradient(135deg, #ffffff 0%, #f0f4ff 100%)',
                'padding': '40px 50px',
                'borderRadius': '20px',
                'width': '520px',
                'boxShadow': '0 12px 30px rgba(0, 0, 0, 0.25)',
                'textAlign': 'left',
                'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                'color': '#333',
                'position': 'relative'
            },
            children=[
                html.H2("Upload data to cloud", style={
                    'marginBottom': '30px',
                    'fontWeight': '700',
                    'fontSize': '2rem',
                    'textAlign': 'center'
                }),

                html.Div([
                    html.H4("Raw intensity data", style={'marginBottom': '8px', 'fontWeight': '600'}),
                    dcc.Upload(
                        id='upload-raw',
                        children=html.Div(["Drag and drop or click to select files"]),
                        style={
                            'padding': '20px',
                            'border': '2px dashed #007BFF',
                            'borderRadius': '12px',
                            'marginBottom': '10px',
                            'cursor': 'pointer',
                            'fontSize': '1rem',
                            'color': '#007BFF',
                            'backgroundColor': '#f9faff',
                            'textAlign': 'center',
                        },
                        multiple=False
                    ),
                    html.Div(id='filename-raw', style={'marginBottom': '20px', 'color': '#007BFF'})
                ]),

                html.Div([
                    html.H4("Concentrations data", style={'marginBottom': '8px', 'fontWeight': '600'}),
                    dcc.Upload(
                        id='upload-concentration',
                        children=html.Div(["Drag and drop or click to select files"]),
                        style={
                            'padding': '20px',
                            'border': '2px dashed #28a745',
                            'borderRadius': '12px',
                            'marginBottom': '10px',
                            'cursor': 'pointer',
                            'fontSize': '1rem',
                            'color': '#28a745',
                            'backgroundColor': '#f4fff7',
                            'textAlign': 'center',
                        },
                        multiple=False
                    ),
                    html.Div(id='filename-concentration', style={'marginBottom': '20px', 'color': '#28a745'})
                ]),

                html.Div([
                    html.H4("CTG data", style={'marginBottom': '8px', 'fontWeight': '600'}),
                    dcc.Upload(
                        id='upload-ctg',
                        children=html.Div(["Drag and drop or click to select files"]),
                        style={
                            'padding': '20px',
                            'border': '2px dashed #fd7e14',
                            'borderRadius': '12px',
                            'marginBottom': '10px',
                            'cursor': 'pointer',
                            'fontSize': '1rem',
                            'color': '#fd7e14',
                            'backgroundColor': '#fff8f1',
                            'textAlign': 'center',
                        },
                        multiple=False
                    ),
                    html.Div(id='filename-ctg', style={'marginBottom': '30px', 'color': '#fd7e14'})
                ]),

                html.Div(
                    style={'display': 'flex', 'justifyContent': 'center', 'gap': '20px'},
                    children=[
                        html.Button('Submit', id='submit-modal', n_clicks=0, style={
                            'padding': '12px 32px',
                            'fontSize': '1rem',
                            'borderRadius': '30px',
                            'border': 'none',
                            'backgroundColor': '#28a745',
                            'color': 'white',
                            'cursor': 'pointer',
                            'fontWeight': '600',
                        }),
                        html.Button('Close', id='close-modal', n_clicks=0, style={
                            'padding': '12px 32px',
                            'fontSize': '1rem',
                            'borderRadius': '30px',
                            'border': 'none',
                            'backgroundColor': '#dc3545',
                            'color': 'white',
                            'cursor': 'pointer',
                            'fontWeight': '600',
                        })
                    ]
                ),

                html.Div(id='upload-alerts', style={'marginTop': '20px'})
            ]
        )
    )


# Layout
app.layout = html.Div([
    html.Div(
        style={
            'height': '70px',
            'padding': '0 15px',
            'background': '#003f5c',
            'color': 'white',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'space-between',
            'fontSize': '30px',
            'fontWeight': '100',
            'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.2)',
            'borderBottom': '5px solid #ed6a28'
        },
        children=[
            html.H1('FetalsenseM V2.1 Dashboard', style={'margin': '0'}),
            html.Button(
                'Upload to cloud', id='upload-cloud-button', n_clicks=0,
                style={
                    'height': '40px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'fontSize': '18px',
                    'marginRight': '0px',
                    'padding': '0 15px',
                    'cursor': 'pointer'
                }
            ),
        ]
    ),
    get_upload_modal(),  # Add modal to layout
    html.Br(),
    # Flex container for the left and right sections
    html.Div([
        # Left side (1/4th width)
        html.Div([
            # Tabs for General, Data Clean, Data Analysis, and Concentrations
            dcc.Tabs(id='left-tabs', children=[
                dcc.Tab(label='General', children=[
                    # File Upload Section inside the General tab
                    html.Div([
                        html.Div([
                            html.H3('File Upload', style={
                                'background': '#003f5c',
                                'padding': '15px',
                                'textAlign': 'center',
                                'color': 'white',
                                'fontWeight': 'bold',
                                'fontSize': '48px'
                            }),
                            dcc.Upload(
                                id='upload-data',
                                children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
                                style={'width': '95%', 'height': '70px', 'lineHeight': '70px',
                                       'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                                       'textAlign': 'center', 'margin': '15px', 'fontSize': '24px'},
                                multiple=False,
                            ),
                        ]),
                        html.Div(id='file-names'),
                        dcc.Store(id='store-file-path'),
                        html.Br(),
                        html.Div([
                            html.H3('Download SNIRF', style={
                                'background': '#003f5c',
                                'padding': '15px',
                                'textAlign': 'center',
                                'color': 'white',
                                'fontWeight': 'bold',
                                'fontSize': '48px'
                            }),
                            html.Button("Download Raw Data SNIRF", id="btn_rawdata_snirf", style={
                                'width': '95%', 'height': '70px', 'lineHeight': '70px',
                                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                                'textAlign': 'center', 'margin': '15px', 'fontSize': '24px'}),
                            dcc.Download(id="download-file-snirf"),
                            dcc.Store(id="snirf-download-status"),
                            html.Div(id='snirf-download-display', style={
    'fontSize': '18px',
    'textAlign': 'center',
    'color': '#2B2D42',
    'marginTop': '10px',
    'fontFamily': 'Courier New'
}),
                        ]),
                        html.Br(),
                        html.Div([
    html.H3('Resampling Options', style={
        'textAlign': 'center', 'fontSize': '40px', 'color': '#003f5c'}),
    dcc.RadioItems(
        id='resample-option',
        options=[
            {'label': '1Hz Averaging', 'value': 'average'},
            {'label': '1Hz Accumulation', 'value': 'accumulation'}
        ],
        value=None,
        labelStyle={'display': 'block', 'fontSize': '40px', 'color': '#003f5c'}
    ),
    html.Div(id='resample-status', style={
        'fontSize': '20px', 'marginTop': '15px', 'textAlign': 'center',
        'color': '#2B2D42', 'fontFamily': 'Courier New'
    }),
], style={'textAlign': 'center', 'marginBottom': '20px'}),
                        html.Br(),
                        html.Div([
                            html.H3('View Intensities', style={
                                'background': '#003f5c',
                                'padding': '15px',
                                'textAlign': 'center',
                                'color': 'white',
                                'fontWeight': 'bold',
                                'fontSize': '48px'
                            }),
                            html.Div([
                                html.H4('Select one or more:', style={
                                    'textAlign': 'left',
                                    'fontSize': '30px',
                                    'marginBottom': '15px',
                                    'color': '#003f5c',
                                    "font-weight": "100"
                                }),
                                dcc.Dropdown(
                                    id='intensities-options-dropdown',
                                    options=[{'label': option, 'value': option} for option in [
                                        'LED_A_782_DET1', 'LED_A_782_DET2', 'LED_A_782_DET3',
                                        'LED_A_801_DET1', 'LED_A_801_DET2', 'LED_A_801_DET3',
                                        'LED_A_808_DET1', 'LED_A_808_DET2', 'LED_A_808_DET3',
                                        'LED_A_828_DET1', 'LED_A_828_DET2', 'LED_A_828_DET3',
                                        'LED_A_848_DET1', 'LED_A_848_DET2', 'LED_A_848_DET3',
                                        'LED_A_887_DET1', 'LED_A_887_DET2', 'LED_A_887_DET3',
                                        'LED_A_DARK_DET1', 'LED_A_DARK_DET2', 'LED_A_DARK_DET3',
                                        'LED_B_782_DET1', 'LED_B_782_DET2', 'LED_B_782_DET3',
                                        'LED_B_801_DET1', 'LED_B_801_DET2', 'LED_B_801_DET3',
                                        'LED_B_808_DET1', 'LED_B_808_DET2', 'LED_B_808_DET3',
                                        'LED_B_828_DET1', 'LED_B_828_DET2', 'LED_B_828_DET3',
                                        'LED_B_848_DET1', 'LED_B_848_DET2', 'LED_B_848_DET3',
                                        'LED_B_887_DET1', 'LED_B_887_DET2', 'LED_B_887_DET3',
                                        'LED_B_DARK_DET1', 'LED_B_DARK_DET2', 'LED_B_DARK_DET3'
                                    ]],
                                    multi=True,
                                    value=[],
                                    style={'borderColor': '#003f5c', 'fontSize': '24px'}
                                )
                            ]),
                            html.Div(id='intensity-selection-status', children='Select to view', style={
                                'fontFamily': 'Courier New',
                                'fontSize': '20px',
                                'textAlign': 'center',
                                'marginTop': '15px',
                                'color': '#2B2D42'
                            }),
                            html.Br(),
                            html.Div([
        html.H4('Select Groups', style={
        'textAlign': 'left',
        'fontSize': '30px',
        'marginBottom': '15px',
        'color': '#003f5c',
        "font-weight": "100"
    }),
    # Group A and Group B selectors placed side by side using flexbox
    html.Div([
        html.Div([
            html.H4('GroupA_Detector1', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupA_dect1_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginRight': '10px'}),

        html.Div([
            html.H4('GroupB_Detector1', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupB_dect1_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginLeft': '10px'})
    ], style={'display': 'flex', 'marginBottom': '10px'}),  # Flexbox for side-by-side
    
    html.Div([
        html.Div([
            html.H4('GroupA_Detector2', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupA_dect2_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginRight': '10px'}),

        html.Div([
            html.H4('GroupB_Detector2', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupB_dect2_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginLeft': '10px'})
    ], style={'display': 'flex', 'marginBottom': '10px'}),

    # Adding GroupB_Detector3 under GroupB_Detector2
    html.Div([
        html.Div([
            html.H4('GroupA_Detector3', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupA_dect3_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginRight': '10px'}),

        html.Div([
            html.H4('GroupB_Detector3', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupB_dect3_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginLeft': '10px'})
    ], style={'display': 'flex', 'marginBottom': '10px'}),

    html.Div([
        html.H4('Select All', style={'fontSize': '20px', 'color': '#cc4c0c', "font-weight": "100"}),
        daq.BooleanSwitch(
            id='select_all_switch',
            on=False,
            style={'transform': 'scale(1.1)', 'padding': '10px'}
        )
    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),
                            ]),
                            dbc.Button('View Intensity Over Time ', id='view-graph-btn', color='primary', style={
                                'padding': '15px', 'width': '100%', 'margin': '15px 0', 'fontSize': '22px'}),
                            html.Div(id='select-intensities', children='Select one or multiple groups', style={
                                'fontFamily': 'Courier New',
                                'fontSize': '20px',
                                'textAlign': 'center',
                                'marginTop': '15px',
                                'color': '#2B2D42'
                            }),
                            html.Br(),
html.Div(children=[
    html.H3('Raw Data Quality Check', style={
        'background': '#003f5c',
        'padding': '15px',
        'textAlign': 'center',
        'color': 'white',
        'fontWeight': 'bold',
        'fontSize': '48px',
    }),
    # Alert and button styles updated for clearer and larger font
    dbc.Alert(
        html.Div([
            html.H4('Signal Noise Ratio', style={'color': '#003f5c', 'marginLeft': '40px', 'textAlign': 'left', 'fontSize': '28px', 'fontWeight': 'lighter'}),
            html.Button('×', id='snr-close-btn', n_clicks=0, style={'background': 'none', 'border': 'none', 'color': 'black', 'fontSize': '28px', 'cursor': 'pointer', 'float': 'right', 'color': '#ed6a28'})
        ]),
        id='snr-alert',  # Unique ID
        is_open=True,
        dismissable=True,
        style={'marginTop': '15px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
    ),
    dbc.Alert(
        html.Div([
            html.H4('Average Signal Noise Ratio', style={'color': '#003f5c', 'marginLeft': '40px', 'textAlign': 'left', 'fontSize': '28px', 'fontWeight': 'lighter'}),
            html.Button('×', id='avg-snr-close-btn', n_clicks=0, style={'background': 'none', 'border': 'none', 'color': 'black', 'fontSize': '28px', 'cursor': 'pointer', 'float': 'right', 'color': '#ed6a28'})
        ]),
        id='avg-snr-alert',  # Unique ID
        is_open=True,
        dismissable=True,
        style={'marginTop': '15px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
    ),
    dbc.Alert(
        html.Div([
            html.H4('Noise Equivalent Power', style={'color': '#003f5c', 'marginLeft': '40px', 'textAlign': 'left', 'fontSize': '28px', 'fontWeight': 'lighter'}),
            html.Button('×', id='nep-close-btn', n_clicks=0, style={'background': 'none', 'border': 'none', 'color': 'black', 'fontSize': '28px', 'cursor': 'pointer', 'float': 'right', 'color': '#ed6a28'})
        ]),
        id='nep-alert',  # Unique ID
        is_open=True,
        dismissable=True,
        style={'marginTop': '15px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
    ),
    dbc.Alert(
        html.Div([
            html.H4('Scatter Plot', style={'color': '#003f5c', 'marginLeft': '40px', 'textAlign': 'left', 'fontSize': '28px', 'fontWeight': 'lighter'}),
            html.Button('×', id='scatter-plot-btn', n_clicks=0, style={'background': 'none', 'border': 'none', 'color': 'black', 'fontSize': '28px', 'cursor': 'pointer', 'float': 'right', 'color': '#ed6a28'})
        ]),
        id='scatter-plot-alert',  # Unique ID
        is_open=True,
        dismissable=True,
        style={'marginTop': '15px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
    ),
    dbc.Alert(
        html.Div([
            html.H4('Distance from Dark', style={'color': '#003f5c', 'marginLeft': '40px', 'textAlign': 'left', 'fontSize': '28px', 'fontWeight': 'lighter'}),
            html.Button('×', id='distance-from-dark-btn', n_clicks=0, style={'background': 'none', 'border': 'none', 'color': 'black', 'fontSize': '28px', 'cursor': 'pointer', 'float': 'right', 'color': '#ed6a28'})
        ]),
        id='distance-from-dark-alert',  # Unique ID
        is_open=True,
        dismissable=True,
        style={'marginTop': '15px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
    ),
    html.Br(),
    html.Div([
                                html.H4('Select one:', style={
                                    'textAlign': 'left',
                                    'fontSize': '30px',
                                    'marginBottom': '15px',
                                    'color': '#003f5c',
                                    "font-weight": "100"
                                }),
                                dcc.Dropdown(
                                    id='data_quality-check-dropdown',
                                    options=[{'label': option, 'value': option} for option in [
                                        'LED_A_782_DET1', 'LED_A_782_DET2', 'LED_A_782_DET3',
                                        'LED_A_801_DET1', 'LED_A_801_DET2', 'LED_A_801_DET3',
                                        'LED_A_808_DET1', 'LED_A_808_DET2', 'LED_A_808_DET3',
                                        'LED_A_828_DET1', 'LED_A_828_DET2', 'LED_A_828_DET3',
                                        'LED_A_848_DET1', 'LED_A_848_DET2', 'LED_A_848_DET3',
                                        'LED_A_887_DET1', 'LED_A_887_DET2', 'LED_A_887_DET3',
                                        'LED_A_DARK_DET1', 'LED_A_DARK_DET2', 'LED_A_DARK_DET3',
                                        'LED_B_782_DET1', 'LED_B_782_DET2', 'LED_B_782_DET3',
                                        'LED_B_801_DET1', 'LED_B_801_DET2', 'LED_B_801_DET3',
                                        'LED_B_808_DET1', 'LED_B_808_DET2', 'LED_B_808_DET3',
                                        'LED_B_828_DET1', 'LED_B_828_DET2', 'LED_B_828_DET3',
                                        'LED_B_848_DET1', 'LED_B_848_DET2', 'LED_B_848_DET3',
                                        'LED_B_887_DET1', 'LED_B_887_DET2', 'LED_B_887_DET3',
                                        'LED_B_DARK_DET1', 'LED_B_DARK_DET2', 'LED_B_DARK_DET3'
                                    ]],
                                    multi=False,
                                    value=[],
                                    style={'borderColor': '#003f5c', 'fontSize': '24px'}
                                )
                            ]),
    dbc.Button('Check Raw Data Quality', id='check-data-quality-btn', color='primary', style={
        'padding': '15px', 'width': '100%', 'margin': '15px 0', 'fontSize': '22px'}),
    html.Div(id='check-raw-data-quality-desc', children='Check data quality', style={
        'fontFamily': 'Courier New',
        'fontSize': '20px',
        'textAlign': 'center',
        'marginTop': '15px',
        'color': '#2B2D42'
    })
]),
]),
]),
]),
#=========================================================================================================================================================================================================================================================================
                # Data Clean Tab
                dcc.Tab(label='Data Clean', children=[
                    html.Div([
                        html.H3('Data Cleaning', style={
                            'background': '#003f5c',
                            'padding': '12px',
                            'textAlign': 'center',
                            'color': '#ECF0F1',
                            'fontWeight': 'bold',
                            'fontSize': '38px',
                            'borderRadius': '8px',
                        }),
                        html.Br(),
                        html.Div(
                                            style={
                                                'background': '#ffffff',
                                                'padding': '20px',
                                                'boxShadow': '0 4px 10px rgba(0, 0, 0, 0.5)',
                                                'marginBottom': '20px'
                                            },
                                            children=[
                                                html.Br(),
                                                # Subtract Dark Section
                html.Br(),
                html.Div('Subtract Dark', style={
                    'background': '#003f5c',
                    'padding': '10px',
                    'textAlign': 'center',
                    'color': 'white',
                    'fontWeight': 'bold',
                    'fontSize': '30px'
                }),
                html.Br(),
                html.Div(
                    children=[
                        dcc.Checklist(
                            id='preprocessing-options-subtract-dark',
                            options=[{'label': 'Subtract Dark', 'value': 'subtract-dark'}],
                            style={'textAlign': 'Center', 'fontSize': '28px', 'marginBottom': '10px', 'color': '#003f5c'},
                            inputStyle={'transform': 'scale(1.5)', 'marginRight': '10px'}
                        ),
                        html.Div('Subtract Noise', style={'fontFamily': 'Courier New', 'fontSize': '16px', 'textAlign': 'center', 'color': '#2B2D42'}),
                        html.Br()
                    ]
                ),
                html.Br(),
                html.Div('High-Pass Filtering', style={
    'background': '#003f5c',
    'padding': '10px',
    'textAlign': 'center',
    'color': 'white',
    'fontWeight': 'bold',
    'fontSize': '30px'
}),
html.Br(),
html.Div(
    children=[
        dcc.Checklist(
            id='preprocessing-options-highpass',
            options=[
                {'label': 'High-Pass Filtering', 'value': 'highpass'},
            ],
            className='alignment-settings-section',
            style={
                'textAlign': 'Center',
                'fontSize': '28px',
                'marginBottom': '10px',
                'color': '#003f5c',
                "font-weight": "100",
                'alignItems': 'center'
            },
            inputStyle={
                'transform': 'scale(1.5)',  # Adjust this value to make the checkbox larger or smaller
                'marginRight': '10px',  # Optional: add space between the checkbox and the label
            }
        ),
        html.Br(),
        # Cutoff Frequency input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Cutoff Frequency (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='highpass-cutoff-input',
                    type='number',
                    min=0.001,
                    max=10000,
                    step=0.001,
                    value=0.001,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Cutoff Frequency for High-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        # Filter Order input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Filter Order',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='highpass-order-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Filter Order for High-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        html.Br(),
        # Sampling Rate Input (Optional)
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Sampling Rate (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='highpass-sampling-rate-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Sampling Rate for High-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        html.Br(),
    ],
),
html.Br(),
html.Br(),
html.Div('Low-Pass Filtering', style={
    'background': '#003f5c',
    'padding': '10px',
    'textAlign': 'center',
    'color': 'white',
    'fontWeight': 'bold',
    'fontSize': '30px'
}),
html.Br(),
html.Div(
    children=[
        dcc.Checklist(
            id='preprocessing-options-lowpass',
            options=[
                {'label': 'Low-Pass Filtering', 'value': 'lowpass'},
            ],
            className='alignment-settings-section',
            style={
                'textAlign': 'Center',
                'fontSize': '28px',
                'marginBottom': '10px',
                'color': '#003f5c',
                "font-weight": "100",
                'alignItems': 'center'
            },
            inputStyle={
                'transform': 'scale(1.5)',  # Adjust this value to make the checkbox larger or smaller
                'marginRight': '10px',  # Optional: add space between the checkbox and the label
            }
        ),
        html.Br(),
        # Cutoff Frequency input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Cutoff Frequency (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='lowpass-cutoff-input',
                    type='number',
                    min=0.001,
                    max=10000,
                    step=0.001,
                    value=0.001,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Cutoff Frequency for Low-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        # Filter Order input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Filter Order',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='lowpass-order-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Filter Order for Low-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        html.Br(),
        # Sampling Rate Input (Optional)
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Sampling Rate (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='lowpass-sampling-rate-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Sampling Rate for Low-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color':  '#003f5c',
            }
        ),
        html.Br(),
        html.Br(),
    ],
),
html.Br(),
html.Br(),
html.Div('Band-Pass Filtering', style={
    'background': '#003f5c',
    'padding': '10px',
    'textAlign': 'center',
    'color': 'white',
    'fontWeight': 'bold',
    'fontSize': '30px'
}),
html.Br(),
html.Div(
    children=[
        dcc.Checklist(
            id='preprocessing-options-bandpass',
            options=[
                {'label': 'Band-Pass Filtering', 'value': 'bandpass'},
            ],
            className='alignment-settings-section',
            style={
                'textAlign': 'Center',
                'fontSize': '28px',
                'marginBottom': '10px',
                'color':  '#003f5c',
                "font-weight": "100",
                'alignItems': 'center'
            },
            inputStyle={
                'transform': 'scale(1.5)',  # Adjust this value to make the checkbox larger or smaller
                'marginRight': '10px',  # Optional: add space between the checkbox and the label
            }
        ),
        html.Br(),
        # Lower Cutoff Frequency input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Lower Cutoff Frequency (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color':  '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='bandpass-lower-cutoff-input',
                    type='number',
                    min=0.001,
                    max=10000,
                    step=0.001,
                    value=0.001,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Lower Cutoff Frequency for Band-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        # Upper Cutoff Frequency input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Upper Cutoff Frequency (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='bandpass-upper-cutoff-input',
                    type='number',
                    min=0.002,
                    max=10001,
                    step=0.002,
                    value=0.002,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Upper Cutoff Frequency for Band-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        html.Br(),
        # Filter Order input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Filter Order',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='bandpass-order-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Filter Order for Band-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#2B2D42'
            }
        ),
        html.Br(),
        html.Br(),
        # Sampling Rate Input (Optional)
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Sampling Rate (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='bandpass-sampling-rate-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Sampling Rate for Band-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#2B2D42'
            }
        ),
        html.Br(),
        html.Br(),
    ],
),
html.Br(),
html.Br(),
html.Br(),
                       
                                                html.Br(),
                                                html.Div('Median Filtering', style={
                                                    'background': '#003f5c',
                                                    'padding': '10px',
                                                    'textAlign': 'center',
                                                    'color': 'white',
                                                    'fontWeight': 'bold',
                                                    'fontSize': '30px'
                                                }),
                                                html.Br(),
                                                html.Div(
                                                    children=[
                                                        dcc.Checklist(
                                                            id='preprocessing-options-median',
                                                            options=[
                                                                {'label': 'Median Filtering', 'value': 'median'},
                                                            ],
                                                            className='alignment-settings-section',
                                                            style={
                                                                'textAlign': 'Center',
                                                                'fontSize': '28px',
                                                                'marginBottom': '10px',
                                                                'color': '#003f5c',
                                                                "font-weight": "100",
                                                                'alignItems': 'center'
                                                            },
                                                            inputStyle={
                                                                'transform': 'scale(1.5)',  # Adjust this value to make the checkbox larger or smaller
                                                                'marginRight': '10px',  # Optional: add space between the checkbox and the label
                                                            }
                                                        ),
                                                        html.Br(),
                                                        html.Div(
                                                            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
                                                            children=[
                                                                html.Div(
                                                                    className='app-controls-name',
                                                                    children='Filter Size',
                                                                    style={
                                                                        'textAlign': 'left',
                                                                        'fontSize': '26px',
                                                                        'marginBottom': '10px',
                                                                        'color': '#003f5c',
                                                                        "font-weight": "100",
                                                                        'marginLeft': '30px'
                                                                    }
                                                                ),
                                                                dcc.Input(
                                                    id='median-filter-size-input',
                                                    type='number',
                                                    min=1,
                                                    max=100,
                                                    step=1,
                                                    value=1,
                                                    style={
                                                        'width': '30%',
                                                        'padding': '5px',
                                                        'height': '24px',  # Increased height to fit the larger font
                                                        'textAlign': 'center',
                                                        'borderColor': '#003f5c',
                                                        'marginRight': '30px',
                                                        'fontSize': '24px'  # Increased font size for the number
                                                        }
                                                        )]
                                                        ),
                                                        html.Div(
                                                            children='Set Filter Size for Median Filtering',
                                                            style={
                                                                'fontFamily': 'Courier New',
                                                                'fontSize': '16px',
                                                                'textAlign': 'center',
                                                                'marginTop': '10px',
                                                                'color': '#2B2D42'
                                                            }
                                                        ),
                                                        html.Br(),
                                                        html.Br(),
                                                        html.Br(),
                                                    ],
                                                ),
                                                html.Div(
                                                    style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
                                                    children=[
                                                        html.Button(
                                                            'Apply',
                                                            id='apply-button',
                                                            n_clicks=0,
                                                            style={'padding': '10px', 'width': '100%', 'margin': '10px 0', 'fontSize': '20px'}
                                                        ),
                                                    ]
                                                ),
                                                html.Div('Apply the selected techniques and parameters set', id='status-apply', style={
                                                'fontFamily': 'Courier New',
                                                'fontSize': '15px',
                                                'textAlign': 'center',
                                                'marginTop': '10px',
                                                'color': '#2B2D42'
                                            }),
                                            ]),
                                            html.Div(
                                                children=[
                                                    html.Div('View Changes', style={
                                                    'background': '#003f5c',
                                                    'padding': '10px',
                                                    'textAlign': 'center',
                                                    'color': 'white',
                                                    'fontWeight': 'bold',
                                                    'fontSize': '30px'
                                                }),
                                                html.Br(),
                                                    html.Br(),
                                            html.Div([
                                                html.H4('Select one or more Groups to view', style={
                                                    'textAlign': 'left',
                                                    'fontSize': '24px',
                                                    'marginBottom': '10px',
                                                    'color': '#003f5c',
                                                    "font-weight": "100"
                                                }),
                                                html.Div([
                                                    html.Div([
                                                        html.H4('GroupA_Detector1', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                        daq.BooleanSwitch(
                                                            id='groupA_dect1_data_clean',
                                                            on=False,
                                                            style={'transform': 'scale(1.1)'}
                                                        ),
                                                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'}),
                                                    html.Div([
                                                        html.H4('GroupA_Detector2', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                        daq.BooleanSwitch(
                                                            id='groupA_dect2_data_clean',
                                                            on=False,
                                                            style={'transform': 'scale(1.1)'}
                                                        ),
                                                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'}),
                                                    html.Div([
                                                        html.H4('GroupA_Detector3', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                        daq.BooleanSwitch(
                                                            id='groupA_dect3_data_clean',
                                                            on=False,
                                                            style={'transform': 'scale(1.1)'}
                                                        ),
                                                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'})
                                                ], style={'display': 'flex'}),
                                            ]),
                                            html.Div([
                                                html.Div([
                                                    html.H4('GroupB_Detector1', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                    daq.BooleanSwitch(
                                                        id='groupB_dect1_data_clean',
                                                        on=False,
                                                        style={'transform': 'scale(1.1)'}
                                                    )
                                                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'}),
                                                html.Div([
                                                    html.H4('GroupB_Detector2', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                    daq.BooleanSwitch(
                                                        id='groupB_dect2_data_clean',
                                                        on=False,
                                                        style={'transform': 'scale(1.1)'}
                                                    )
                                                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'}),
                                                html.Div([
                                                    html.H4('GroupB_Detector3', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                    daq.BooleanSwitch(
                                                        id='groupB_dect3_data_clean',
                                                        on=False,
                                                        style={'transform': 'scale(1.1)'}
                                                    )
                                                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'})
                                            ], style={'display': 'flex'}),
                                                    html.Br(),
                                                    html.Div(
                                                        style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
                                                        children=[
                                                            html.Div(
                                                                children='View spectra',
                                                                style={'textAlign': 'left', 'fontSize': '24px', 'marginBottom': '10px', 'color': '#003f5c', "font-weight": "100", 'marginLeft': '30px'}
                                                            ),
                                                            html.Button(
                                                                'View',
                                                                id='view-button',
                                                                style={'padding': '10px', 'width': '50%', 'margin': '10px 0', 'fontSize': '20px'},
                                                                n_clicks=0                                        
                                                            )
                                                        ],
                                                    ),
                                                   html.Div(
                                                        children='Select Show to view the spectra',
                                                        style={
                                                            'fontFamily': 'Courier New',
                                                            'fontSize': '15px',
                                                            'textAlign': 'center',
                                                            'marginTop': '10px',
                                                            'color': '#2B2D42'
                                                        },
                                                ),
                    ]),
                ]),
                ]),
                dcc.Tab(label='Data Analysis', children=[
                    html.Div([
                        html.H3('Data Analysis', style={
                            'background': '#003f5c',
                            'padding': '12px',
                            'textAlign': 'center',
                            'color': '#ECF0F1',
                            'fontWeight': 'bold',
                            'fontSize': '38px',
                            'borderRadius': '8px',
                        }),
                        html.Br(),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Histogram',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-histogram-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='histogram-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Standard Deviation',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-standard-deviation-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='standard-deviation-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Mean', style={'color': '#003f5c', 'marginLeft': '40px',
                                                                               'textAlign': 'left', 'fontSize': '24px',
                                                                               'fontWeight': 'lighter',
                                                                               'display': 'inline-block',
                                                                               'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-mean-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='mean-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Maximum',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-maximum-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='maximum-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Minimum',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-minimum-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='minimum-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Largest Variations',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-variations-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='variations-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Scatter Effect',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-scatter-effect-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px'
                                                            }
                                                        )
                                                    ]),
                                                    id='scatter-effect-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('3D Plot',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='3d-plot-effect-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='3d-effect-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                html.Br(),
                                                html.Br(),
                                                html.Div([
                                                    html.H4('Select intensity:', style={
                                                        'textAlign': 'left',
                                                        'fontSize': '28px',
                                                        'marginBottom': '10px',
                                                        'color': '#003f5c',
                                                        "font-weight": "100",
                                                        'opacity': 0.5,
                                                        # Make text
                                                        # semi-transparent to
                                                        # indicate it's not
                                                        # clickable
                                                    }),
                                                    dcc.Dropdown(
                                                        id='data-analysis-options-dropdown',
                                                        options=[{'label': option, 'value': option} for option in
                                                                 ['GroupA_Detector1', 'GroupA_Detector2',
                                                                  'GroupB_Detector1', 'GroupB_Detector2']],
                                                        multi=False,
                                                        value=[],
                                                        style={
                                                            'borderColor': 'transparent',  # Make the border transparent
                                                            'backgroundColor': 'transparent',
                                                            # Make background
                                                            # transparent
                                                            'fontSize': '24px',
                                                            'cursor': 'not-allowed',  # Set cursor to not-allowed
                                                            'opacity': 0.5
                                                            # Make dropdown
                                                            # semi-transparent
                                                            # to indicate it's
                                                            # not clickable
                                                        }
                                                    ),
                                                ]),
                                                html.Div(
                                                    style={
                                                        'display': 'flex',
                                                        'alignItems': 'center',
                                                        'justifyContent': 'space-between',
                                                        'opacity': 0.5,  # Make the button's div semi-transparent
                                                    },
                                                    children=[
                                                        html.Button(
                                                            'Perform Data Analysis',
                                                            id='data-analysis-button',
                                                            n_clicks=0,
                                                            style={
                                                                'padding': '10px',
                                                                'width': '100%',
                                                                'margin': '10px 0',
                                                                'fontSize': '20px',
                                                                'backgroundColor': 'transparent',
                                                                # Make button
                                                                # background
                                                                # transparent
                                                                'border': 'none',
                                                                # Remove border
                                                                # to make it
                                                                # look inactive
                                                                'cursor': 'not-allowed',  # Set cursor to not-allowed
                                                                'opacity': 0.5  # Make button semi-transparent
                                                            }
                                                        ),
                                                    ]
                                                ),
                    ]),
                ]),
                dcc.Tab(label='Concentrations', children=[
        html.Div([
            html.H3('Concentrations', style={
                'background': '#003f5c',
                'padding': '12px',
                'textAlign': 'center',
                'color': '#ECF0F1',
                'fontWeight': 'bold',
                'fontSize': '38px',
                'borderRadius': '8px',
            }),
            # Add the "Calculate Concentrations" button here
            html.Button('Calculate Concentrations', id='calculate-concentrations-btn', n_clicks=0, style={
                                'width': '95%', 'height': '70px', 'lineHeight': '70px',
                                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                                'textAlign': 'center', 'margin': '15px', 'fontSize': '24px'}),
            html.Br(),
            html.Button('Download Concentrations Excel File', id='download_concentrations_excel_btn',  n_clicks=0, style={
                                'width': '95%', 'height': '70px', 'lineHeight': '70px',
                                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                                'textAlign': 'center', 'margin': '15px', 'fontSize': '24px'}),
            dcc.Download(id="download-conc-xlsx"),
        html.Div(id='tabs-container'),
        ]),
    ]),
]),
        ], style={'width': '25%', 'padding': '15px', 'boxSizing': 'border-box'}),
        # Right side (3/4th width for Plot Section)
        html.Div([
            html.H3('Plot Section', style={
                'background': '#003f5c',
                'padding': '12px',
                'textAlign': 'center',
                'color': '#ECF0F1',
                'fontWeight': 'bold',
                'fontSize': '38px',
                'borderRadius': '8px',
            }),
            dcc.Tabs(id='tabs', children=[
                dcc.Tab(label='Intensity vs Time', children=[
                    html.Div(id='intensity-time-plot'),
                ]),
                dcc.Tab(label='Data Quality Check', children=[
                    html.Div(id='data-quality-plot'),
                ]),
                dcc.Tab(label='Data Clean', children=[
                    html.Div(id='data-clean-plot'),
                ]),
                dcc.Tab(label='Concentrations', children=[
                    html.Div(id='concentrations-plot'),
                ]),
            ]),
        ], style={'width': '75%', 'padding': '10px', 'boxSizing': 'border-box', 'borderLeft': '2px solid #3498DB'})
    ], style={'display': 'flex', 'height': '100vh'}),
    dcc.Store(id='uploaded-data'),
    dcc.Store(id='resampled-data'),
    dcc.Store(id='resampling-method'),
    dcc.Store(id='quality-metrics'),
    dcc.Store(id='cleaned-data'),
    dcc.Store(id='concentrations'),
    dcc.Store(id='excel-path')
])

UPLOAD_FOLDER = 'src/uploads'
COLUMN_NAMES = [
    'Time', 'System Time (s)', 'Sample Time (s)', 'LED_A_782_DET1', 'LED_A_782_DET2', 'LED_A_782_DET3',
    'LED_A_801_DET1', 'LED_A_801_DET2', 'LED_A_801_DET3', 'LED_A_808_DET1', 'LED_A_808_DET2', 'LED_A_808_DET3',
    'LED_A_828_DET1', 'LED_A_828_DET2', 'LED_A_828_DET3', 'LED_A_848_DET1', 'LED_A_848_DET2', 'LED_A_848_DET3',
    'LED_A_887_DET1', 'LED_A_887_DET2', 'LED_A_887_DET3', 'LED_A_DARK_DET1', 'LED_A_DARK_DET2', 'LED_A_DARK_DET3',
    'LED_B_782_DET1', 'LED_B_782_DET2', 'LED_B_782_DET3', 'LED_B_801_DET1', 'LED_B_801_DET2', 'LED_B_801_DET3',
    'LED_B_808_DET1', 'LED_B_808_DET2', 'LED_B_808_DET3', 'LED_B_828_DET1', 'LED_B_828_DET2', 'LED_B_828_DET3',
    'LED_B_848_DET1', 'LED_B_848_DET2', 'LED_B_848_DET3', 'LED_B_887_DET1', 'LED_B_887_DET2', 'LED_B_887_DET3',
    'LED_B_DARK_DET1', 'LED_B_DARK_DET2', 'LED_B_DARK_DET3', 'Accelerometer X axis', 'Accelerometer Y axis',
    'Accelerometer Z axis', 'Gyroscope X axis', 'Gyroscope Y axis', 'Gyroscope Z axis', 'PCB Temp', 'Skin Temp'
]

def clear_folder(folder_path):
    """Delete all files in the specified folder."""
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

@app.callback(
    Output("file-names", "children"),
    Output("uploaded-data", "data"),
    State("upload-data", "filename"),
    Input("upload-data", "contents"),
)
def save_uploaded_file(filename, contents):
    if contents is None or filename is None:
        return "No file uploaded yet.", None

    # Clear existing files in the upload folder
    clear_folder(UPLOAD_FOLDER)

    # Decode file content
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        decoded_str = decoded.decode('utf-8')
    except UnicodeDecodeError:
        return "Error: File is not UTF-8 encoded. Upload data in CSV format", None

    # Save to file
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    with open(file_path, 'wb') as f:
        f.write(decoded)

    # Parse CSV if valid
    if filename.endswith('.csv'):
        df = pd.read_csv(io.StringIO(decoded_str), skiprows=10, names=COLUMN_NAMES)
        data_json = df.to_json(date_format='iso', orient='split')
        return f"File '{filename}' uploaded successfully with {len(df)} rows.", data_json
    else:
        return f"File '{filename}' uploaded successfully, but it is not a CSV file.", None

from datetime import datetime

def parse_time(time_str):
    """Convert various time string formats to total seconds as float."""
    try:
        if isinstance(time_str, (int, float)):
            return float(time_str)

        time_str = str(time_str).strip()

        # Try parsing with full format first
        try:
            dt = datetime.strptime(time_str, "%H:%M:%S.%f")
            return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6
        except ValueError:
            pass

        # Try various fallback formats
        for fmt in ("%M:%S.%f", "%S.%f", "%H:%M:%S", "%M:%S", "%S"):
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6
            except ValueError:
                continue

        # Try manual parsing for flexible formats
        parts = time_str.split(":")
        if len(parts) == 3:  # H:M:S(.ms)
            h, m, s = parts
            s_parts = s.split(".")
            sec = int(s_parts[0])
            ms = int(s_parts[1]) / 1000 if len(s_parts) > 1 else 0
            return int(h) * 3600 + int(m) * 60 + sec + ms
        elif len(parts) == 2:  # M:S(.ms)
            m, s = parts
            s_parts = s.split(".")
            sec = int(s_parts[0])
            ms = int(s_parts[1]) / 1000 if len(s_parts) > 1 else 0
            return int(m) * 60 + sec + ms
        elif "." in time_str:  # S.ms
            sec, ms = time_str.split(".")
            return int(sec) + int(ms) / 1000
        else:
            return float(time_str)

    except Exception as e:
        print(f"❌ Failed to parse time: {time_str} | Error: {e}")
        return None
@app.callback(
    Output('resample-status', 'children'),
    Output('resampled-data', 'data'),
    Output('resampling-method', 'data'),
    Input('resample-option', 'value'),
    State('uploaded-data', 'data'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def on_resample_option_selected(option, uploaded_data_json, original_filename):
    if uploaded_data_json is None or original_filename is None:
        return "⚠️ No uploaded data available.", None, "No resampling"

    df = pd.read_json(uploaded_data_json, orient='split')

    # Step 1: Parse Time column to total seconds
    try:
        df['total_seconds'] = df['Time'].apply(parse_time)
    except Exception:
        return "⚠️ Time format parsing error.", None, "No resampling"

    if df['total_seconds'].isnull().any():
        return "⚠️ Time format error in one or more rows.", None, "No resampling"

    # Step 2: Group by integer seconds
    grouped = df.groupby('total_seconds')

    if option == 'average':
        resampled_df = grouped.mean(numeric_only=True)
        resample_method_str = "1Hz Average"
    elif option == 'accumulation':
        resampled_df = grouped.sum(numeric_only=True)
        resample_method_str = "1Hz Accumulation"
    else:
        return f"⚠️ Unknown resampling option: {option}", None, "No resampling"

    # Step 3: Reduce original time column to one row per second (HH:MM:SS)
    def reduce_to_one_per_second(time_series):
        seen_seconds = set()
        reduced = []
        for t in time_series:
            try:
                time_parts = t.split(':')
                minutes = time_parts[1]
                seconds = time_parts[2].split('.')[0]
                reduced_time = f"{time_parts[0]}:{minutes}:{seconds}"
                if reduced_time not in seen_seconds:
                    seen_seconds.add(reduced_time)
                    reduced.append(t)
            except:
                continue
        return reduced

    reduced_time_list = reduce_to_one_per_second(df['Time'].tolist())

    # Step 4: Insert Time column
    if len(reduced_time_list) == len(resampled_df):
        resampled_df.insert(0, 'Time', reduced_time_list)
    else:
        fallback_times = resampled_df.index.map(lambda x: f"{int(x // 60):02}:{int(x % 60):02}:00.000")
        resampled_df.insert(0, 'Time', fallback_times)

    # Step 5: Drop irrelevant columns
    for col in ['System Time (s)', 'Sample Time (s)']:
        if col in resampled_df.columns:
            resampled_df.drop(columns=col, inplace=True)

    # Step 6: Save resampled data to disk
    RESAMPLED_FOLDER = 'src/resampled_data'
    os.makedirs(RESAMPLED_FOLDER, exist_ok=True)
    clear_folder(RESAMPLED_FOLDER)

    base_name = os.path.splitext(original_filename)[0]
    resampled_filename = f"{base_name}_resampled_data.csv"
    resampled_path = os.path.join(RESAMPLED_FOLDER, resampled_filename)
    resampled_df.to_csv(resampled_path, index=False)

    # Step 7: Return updated info
    resampled_json = resampled_df.to_json(date_format='iso', orient='split')
    return f"✅ Resampled using: {resample_method_str}", resampled_json, resample_method_str

@app.callback(
    Output("download-file-snirf", "data"),
    Output("snirf-download-status", "data"),
    Input("btn_rawdata_snirf", "n_clicks"),
    State("upload-data", "filename"),
    prevent_initial_call=True
)
def generate_and_download_raw_snirf(n_clicks, filename):
    if not n_clicks:
        return no_update, no_update

    if not filename:
        return no_update, no_update

    try:
        # Call the SNIRF file creation function
        snirf_path, snirf_name = create_snirf(filename)

        # Ensure file exists
        if snirf_path and os.path.exists(snirf_path):
            return dcc.send_file(snirf_path), snirf_name

    except Exception as e:
        print(f"Error generating/downloading SNIRF: {e}")
    
    return no_update, no_update

#===============Create intensity plots=============================================================================================================================
GROUPS = {
    'GroupA_Detector1': ['LED_A_782_DET1', 'LED_A_801_DET1', 'LED_A_808_DET1', 'LED_A_828_DET1', 'LED_A_848_DET1', 'LED_A_887_DET1', 'LED_A_DARK_DET1'],
    'GroupA_Detector2': ['LED_A_782_DET2', 'LED_A_801_DET2', 'LED_A_808_DET2', 'LED_A_828_DET2', 'LED_A_848_DET2', 'LED_A_887_DET2', 'LED_A_DARK_DET2'],
    'GroupA_Detector3': ['LED_A_782_DET3', 'LED_A_801_DET3', 'LED_A_808_DET3', 'LED_A_828_DET3', 'LED_A_848_DET3', 'LED_A_887_DET3', 'LED_A_DARK_DET3'],
    'GroupB_Detector1': ['LED_B_782_DET1', 'LED_B_801_DET1', 'LED_B_808_DET1', 'LED_B_828_DET1', 'LED_B_848_DET1', 'LED_B_887_DET1', 'LED_B_DARK_DET1'],
    'GroupB_Detector2': ['LED_B_782_DET2', 'LED_B_801_DET2', 'LED_B_808_DET2', 'LED_B_828_DET2', 'LED_B_848_DET2', 'LED_B_887_DET2', 'LED_B_DARK_DET2'],
    'GroupB_Detector3': ['LED_B_782_DET3', 'LED_B_801_DET3', 'LED_B_808_DET3', 'LED_B_828_DET3', 'LED_B_848_DET3', 'LED_B_887_DET3', 'LED_B_DARK_DET3'],
}

import numpy as np
import plotly.graph_objs as go

def create_intensity_figure(df, spectra_list, title, time_unit):
    traces = []
    for col in spectra_list:
        if col in df.columns:
            y = df[col].values
            if len(y) == 0:
                continue
            x = df['total_seconds'] if 'total_seconds' in df.columns else np.arange(len(y))
            traces.append(go.Scatter(x=x, y=y, mode='lines', name=col))

    layout = go.Layout(
        title={'text': title, 'font': {'size': 24}},
        xaxis={'title': f'Time ({time_unit})', 'title_font': {'size': 18}, 'tickfont': {'size': 14}},
        yaxis={'title': 'Voltage (V)', 'title_font': {'size': 18}, 'tickfont': {'size': 14}},
        legend={'font': {'size': 14}},
        height=1050,
        width=2140,
        autosize=False  # Disable auto-resizing to enforce fixed height
    )

    fig = go.Figure(data=traces, layout=layout)
    fig.update_layout(
        margin=dict(l=60, r=40, t=80, b=60),  # Optional: adjust margins
    )
    return fig


@app.callback(
    Output('intensity-time-plot', 'children'),
    Input('view-graph-btn', 'n_clicks'),
    State('resampled-data', 'data'),
    State('uploaded-data', 'data'),
    State('intensities-options-dropdown', 'value'),
    State('groupA_dect1_spectras', 'on'),
    State('groupA_dect2_spectras', 'on'),
    State('groupA_dect3_spectras', 'on'),
    State('groupB_dect1_spectras', 'on'),
    State('groupB_dect2_spectras', 'on'),
    State('groupB_dect3_spectras', 'on'),
    State('select_all_switch', 'on'),
    prevent_initial_call=True
)
def update_intensity_plot(n_clicks, resampled_json, uploaded_json, selected_spectra,
                          groupA1, groupA2, groupA3, groupB1, groupB2, groupB3, select_all):
    if not n_clicks:
        return html.Div("Click 'View Intensity Over Time' to generate plots.")

    # Load data
    if resampled_json:
        df = pd.read_json(resampled_json, orient='split')
        time_unit = 's'
    else:
        df = pd.read_json(uploaded_json, orient='split')
        time_unit = 'ms'

    if df is None or df.empty:
        return html.Div("No data available for plotting.")

    # If select all is toggled, override all
    if select_all:
        groupA1 = groupA2 = groupA3 = groupB1 = groupB2 = groupB3 = True

    tabs = []

    def add_tab(label, group_key):
        fig = create_intensity_figure(df, GROUPS[group_key], label, time_unit)
        tabs.append(
            dcc.Tab(
                label=label,
                children=[
                    dcc.Graph(
                        figure=fig,
                        config={'responsive': True},
                        style={'height': '1000px', 'width': '100%'}
                    )
                ]
            )
        )

    if groupA1: add_tab("GroupA_Detector1", 'GroupA_Detector1')
    if groupA2: add_tab("GroupA_Detector2", 'GroupA_Detector2')
    if groupA3: add_tab("GroupA_Detector3", 'GroupA_Detector3')
    if groupB1: add_tab("GroupB_Detector1", 'GroupB_Detector1')
    if groupB2: add_tab("GroupB_Detector2", 'GroupB_Detector2')
    if groupB3: add_tab("GroupB_Detector3", 'GroupB_Detector3')

    if selected_spectra:
        fig = create_intensity_figure(df, selected_spectra, "Selected Intensities", time_unit)
        tabs.append(
            dcc.Tab(
                label="Selected Intensities",
                children=[
                    dcc.Graph(
                        figure=fig,
                        config={'responsive': True},
                        style={'height': '1000px', 'width': '100%'}
                    )
                ]
            )
        )

    return dcc.Tabs(children=tabs)


#======================DATA QUALITY CHECK======================================================================================================================

@app.callback(
    Output('data-quality-plot', 'children'),
    Output('quality-metrics', 'data'),  # NEW OUTPUT
    Input('check-data-quality-btn', 'n_clicks'),
    State('resampled-data', 'data'),
    State('uploaded-data', 'data'),
    State('data_quality-check-dropdown', 'value'),
    prevent_initial_call=True
)
def update_data_quality_tab(n_clicks, resampled_json, uploaded_json, selected_col):
    if not n_clicks:
        return no_update, no_update

    df = pd.read_json(resampled_json or uploaded_json, orient='split')

    if df is None or df.empty:
        return html.Div("No data available for quality check."), no_update

    snr_hist_fig, snr_plot, snr_bar_chart, nep_bar_chart, scatter_plot, distance_to_dark_plot = data_quality_check(df, selected_col)

    # Extract values for storing
    snr_vals = snr_bar_chart['data'][0]['y']  # SNR Group 1, 2, 3
    nep_vals = nep_bar_chart['data'][0]['y']  # NEP Group 1, 2, 3

    metrics = {
        "SNR Short (A1 + B3)": snr_vals[0],
        "SNR Mid (A2 + B2)": snr_vals[1],
        "SNR Long (A3 + B1)": snr_vals[2],
        "NEP DET 1": nep_vals[0],
        "NEP DET 2": nep_vals[1],
        "NEP DET 3": nep_vals[2],
    }

    return html.Div([
        html.Div(dcc.Graph(figure=snr_hist_fig)),
        html.Div(dcc.Graph(figure=snr_plot)),
        html.Div([
            html.Div(dcc.Graph(figure=snr_bar_chart), style={'display': 'inline-block', 'width': '48%'}),
            html.Div(dcc.Graph(figure=nep_bar_chart), style={'display': 'inline-block', 'width': '48%'}),
        ]),
        html.Div(dcc.Graph(figure=scatter_plot)),
        html.Div(dcc.Graph(figure=distance_to_dark_plot))
    ]), metrics


#============================DATA CLEANING================================================================================================================

@app.callback(
    Output('data-clean-plot', 'children'),
    Output('cleaned-data', 'data'),
    Input('apply-button', 'n_clicks'),
    Input('view-button', 'n_clicks'),
    State('resampled-data', 'data'),
    State('uploaded-data', 'data'),
    State('upload-data', 'filename'),
    State('preprocessing-options-subtract-dark', 'value'),
    State('preprocessing-options-highpass', 'value'),
    State('highpass-cutoff-input', 'value'),
    State('highpass-order-input', 'value'),
    State('highpass-sampling-rate-input', 'value'),
    State('preprocessing-options-lowpass', 'value'),
    State('lowpass-cutoff-input', 'value'),
    State('lowpass-order-input', 'value'),
    State('lowpass-sampling-rate-input', 'value'),
    State('preprocessing-options-bandpass', 'value'),
    State('bandpass-lower-cutoff-input', 'value'),
    State('bandpass-upper-cutoff-input', 'value'),
    State('bandpass-order-input', 'value'),
    State('bandpass-sampling-rate-input', 'value'),
    State('preprocessing-options-median', 'value'),
    State('median-filter-size-input', 'value'),
    State('groupA_dect1_data_clean', 'on'),
    State('groupA_dect2_data_clean', 'on'),
    State('groupA_dect3_data_clean', 'on'),
    State('groupB_dect1_data_clean', 'on'),
    State('groupB_dect2_data_clean', 'on'),
    State('groupB_dect3_data_clean', 'on'),
    prevent_initial_call=True
)
def data_cleaning(apply_clicks, view_clicks, resampled_json, uploaded_json, uploaded_filename,
                  subtract_dark_option,
                  highpass_option, highpass_cutoff, highpass_order, highpass_sr,
                  lowpass_option, lowpass_cutoff, lowpass_order, lowpass_sr,
                  bandpass_option, bandpass_low, bandpass_high, bandpass_order, bandpass_sr,
                  median_option, median_size,
                  groupA1, groupA2, groupA3, groupB1, groupB2, groupB3):

    triggered_id = callback_context.triggered_id
    if triggered_id not in ['apply-button', 'view-button']:
        return dash.no_update, dash.no_update

    data_json = resampled_json if resampled_json else uploaded_json
    if not data_json:
        return html.Div("No data available."), dash.no_update

    df = pd.read_json(data_json, orient='split')
    if df.empty:
        return html.Div("Loaded data is empty."), dash.no_update

    original_time_df = pd.read_json(resampled_json if resampled_json else uploaded_json, orient='split')
    time_axis = original_time_df['Time'] if 'Time' in original_time_df.columns else original_time_df.index

    signal_cols = [col for col in df.columns if 'LED' in col]
    original_signal_df = df[signal_cols].copy()
    cleaned_df = original_signal_df.copy()

    if subtract_dark_option and 'subtract-dark' in subtract_dark_option:
        dark_mapping = {
            f"LED_A_{wl}_DET{i}": f"LED_A_DARK_DET{i}"
            for wl in ['782', '801', '808', '828', '848', '887'] for i in [1, 2, 3]
        }
        dark_mapping.update({
            f"LED_B_{wl}_DET{i}": f"LED_B_DARK_DET{i}"
            for wl in ['782', '801', '808', '828', '848', '887'] for i in [1, 2, 3]
        })
        for main_col, dark_col in dark_mapping.items():
            if main_col in cleaned_df.columns and dark_col in df.columns:
                cleaned_df[main_col] -= df[dark_col]
        cleaned_df.drop(columns=[col for col in cleaned_df.columns if 'DARK' in col], inplace=True)

    numeric_cols = cleaned_df.select_dtypes(include='number').columns

    if highpass_option and 'highpass' in highpass_option:
        if highpass_cutoff <= 0 or highpass_cutoff >= (highpass_sr / 2):
            return html.Div(f"Invalid high-pass cutoff. Must be between 0 and {highpass_sr / 2} Hz."), dash.no_update
        b, a = butter(highpass_order, highpass_cutoff, btype='highpass', fs=highpass_sr)
        for col in numeric_cols:
            cleaned_df[col] = filtfilt(b, a, cleaned_df[col].values)

    if lowpass_option and 'lowpass' in lowpass_option:
        if lowpass_cutoff <= 0 or lowpass_cutoff >= (lowpass_sr / 2):
            return html.Div(f"Invalid low-pass cutoff. Must be between 0 and {lowpass_sr / 2} Hz."), dash.no_update
        b, a = butter(lowpass_order, lowpass_cutoff, btype='lowpass', fs=lowpass_sr)
        for col in numeric_cols:
            cleaned_df[col] = filtfilt(b, a, cleaned_df[col].values)

    if bandpass_option and 'bandpass' in bandpass_option:
        if bandpass_low <= 0 or bandpass_high <= bandpass_low or bandpass_high >= (bandpass_sr / 2):
            return html.Div(f"Invalid band-pass range. Must be: 0 < low < high < {bandpass_sr / 2} Hz."), dash.no_update
        b, a = butter(bandpass_order, [bandpass_low, bandpass_high], btype='bandpass', fs=bandpass_sr)
        for col in numeric_cols:
            cleaned_df[col] = filtfilt(b, a, cleaned_df[col].values)

    if median_option and 'median' in median_option:
        for col in numeric_cols:
            cleaned_df[col] = medfilt(cleaned_df[col].values, kernel_size=median_size)

    cleaned_df.insert(0, 'Time', time_axis)

    grouped_columns = {
        "Group A Detector 1": [f"LED_A_{wl}_DET1" for wl in ['782', '801', '808', '828', '848', '887']],
        "Group A Detector 2": [f"LED_A_{wl}_DET2" for wl in ['782', '801', '808', '828', '848', '887']],
        "Group A Detector 3": [f"LED_A_{wl}_DET3" for wl in ['782', '801', '808', '828', '848', '887']],
        "Group B Detector 1": [f"LED_B_{wl}_DET1" for wl in ['782', '801', '808', '828', '848', '887']],
        "Group B Detector 2": [f"LED_B_{wl}_DET2" for wl in ['782', '801', '808', '828', '848', '887']],
        "Group B Detector 3": [f"LED_B_{wl}_DET3" for wl in ['782', '801', '808', '828', '848', '887']]
    }

    active_groups = {
        "Group A Detector 1": groupA1,
        "Group A Detector 2": groupA2,
        "Group A Detector 3": groupA3,
        "Group B Detector 1": groupB1,
        "Group B Detector 2": groupB2,
        "Group B Detector 3": groupB3,
    }

    plots = []
    for group_name, enabled in active_groups.items():
        if not enabled:
            continue

        group_signals = grouped_columns[group_name]
        group_figs = []

        for col in group_signals:
            if col not in original_signal_df.columns or col not in cleaned_df.columns:
                continue

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=time_axis, y=original_signal_df[col], name=f"{col} - Raw", line=dict(dash='dot')))
            fig.add_trace(go.Scatter(x=time_axis, y=cleaned_df[col], name=f"{col} - Cleaned", line=dict(dash='solid')))
            fig.update_layout(
                title=f"{col} Comparison",
                xaxis_title='Time',
                yaxis_title='Voltage',
                height=400,
                legend=dict(font=dict(size=10))
            )
            group_figs.append(dcc.Graph(figure=fig))

        if group_figs:
            plots.append(html.Div([
                html.H4(group_name, style={'color': '#003f5c', 'marginTop': '20px'}),
                *group_figs
            ]))

    save_dir = "src/cleaned_data/data_clean"
    os.makedirs(save_dir, exist_ok=True)

    for file in os.listdir(save_dir):
        try:
            os.remove(os.path.join(save_dir, file))
        except Exception as e:
            print(f"Error deleting file: {e}")

    base_name = os.path.splitext(uploaded_filename)[0] if uploaded_filename else "resampled_data"
    csv_path = os.path.join(save_dir, f"{base_name}_cleaned.csv")

    try:
        cleaned_df.to_csv(csv_path, index=False)
        print(f"✅ Cleaned data saved to: {csv_path}")
    except Exception as e:
        print(f"❌ Failed to save cleaned CSV: {e}")

    if not plots:
        return html.Div("No groups selected or no matching data found."), cleaned_df.to_json(orient='split')

    return html.Div(plots), cleaned_df.to_json(orient='split')


@app.callback(
    Output('concentrations-plot', 'children'),
    Output('concentrations', 'data'),  
    Input('calculate-concentrations-btn', 'n_clicks'),
    State('cleaned-data', 'data'),
    State('resampled-data', 'data'),
    State('uploaded-data', 'data'),
    State('resampling-method', 'data'),  # <-- NEW
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def on_calculate_concentrations(n_clicks, cleaned_json, resampled_json, uploaded_json, resampling_method, filename):
    if not n_clicks:
        return dash.no_update, dash.no_update

    # Priority: Cleaned > Resampled > Raw
    df = None
    resample_note = resampling_method or "No resampling"

    if cleaned_json:
        df = pd.read_json(cleaned_json, orient='split')
        resample_note += ""
    elif resampled_json:
        df = pd.read_json(resampled_json, orient='split')
        resample_note += ""
    elif uploaded_json:
        df = pd.read_json(uploaded_json, orient='split')
        resample_note = "No Resampling"

    if df is None or df.empty:
        return html.Div("❌ No valid data to calculate concentrations."), dash.no_update

    # Extract relevant columns
    selected_cols = [col for col in df.columns if col.startswith("LED_") or col == "Time"]
    df_selected = df[selected_cols]

    # Run calculations
    conc_a_1_df, conc_a_2_df, conc_a_3_df, \
    conc_b_1_df, conc_b_2_df, conc_b_3_df, \
    atten_a_1, atten_a_2, atten_a_3, \
    atten_b_1, atten_b_2, atten_b_3, wavelengths = UCLN(df_selected)

    sto2_result = SRS(df_selected)
    df_sto2_A = pd.DataFrame({"Sto2_A": sto2_result["StO2_A"]})
    df_sto2_B = pd.DataFrame({"Sto2_B": sto2_result["StO2_B"]})

    ds_sto2_result = dual_slope_wavelength(df_selected)
    df_sto2_dual = pd.DataFrame({"dual_slope_sto2": ds_sto2_result["ds_sto2_AB"]})

    # Generate Excel
    output_dir = os.path.join(os.path.dirname(__file__), "src", "concentrations_ucln_srs", "concentration_data")
    os.makedirs(output_dir, exist_ok=True)

    excel_path = generate_concentration_excel(
        filename=filename,
        resample_note=resample_note,
        df=df,
        conc_a_1_df=conc_a_1_df,
        conc_a_2_df=conc_a_2_df,
        conc_a_3_df=conc_a_3_df,
        conc_b_1_df=conc_b_1_df,
        conc_b_2_df=conc_b_2_df,
        conc_b_3_df=conc_b_3_df,
        df_sto2_A=df_sto2_A,
        df_sto2_B=df_sto2_B,
        df_sto2_dual=df_sto2_dual,
        output_dir=output_dir
    )

    # Prepare plots
    tabs = []
    sheet_data = {
        "Concentration LED A-DET 1": conc_a_1_df,
        "Concentration LED A-DET 2": conc_a_2_df,
        "Concentration LED A-DET 3": conc_a_3_df,
        "Concentration LED B-DET 1": conc_b_1_df,
        "Concentration LED B-DET 2": conc_b_2_df,
        "Concentration LED B-DET 3": conc_b_3_df,
        "Tissue oxygen saturation(StO2) LED A": df_sto2_A,
        "Tissue oxygen saturation(StO2) LED B": df_sto2_B,
        "Tissue oxygen saturation(StO2) Dual Slope": df_sto2_dual
    }

    for name, df_plot in sheet_data.items():
        if not df_plot.empty:
            fig = px.line(df_plot, title=name)
            fig.update_layout(
                xaxis_title="Time",
                yaxis_title="ΔC (mM)" if "Concentration" in name else "StO2 (%)"
            )
            tab_label = (
                "StO₂ - LED A" if "LED A" in name else
                "StO₂ - LED B" if "LED B" in name else
                "StO₂ - Dual" if "Dual Slope" in name else
                name[:31]
            )
            tabs.append(dcc.Tab(label=tab_label, children=[
                html.Div([
                    html.H5(name),
                    dcc.Graph(figure=fig, style={'height': '70vh'})
                ])
            ]))

    return dcc.Tabs(children=tabs), {
        "preview": {name: df.head().to_dict('records') for name, df in sheet_data.items()},
        "excel_path": excel_path
    }


import os
import numpy as np
import pandas as pd

def generate_concentration_excel(
    filename, resample_note, df,
    conc_a_1_df, conc_a_2_df, conc_a_3_df,
    conc_b_1_df, conc_b_2_df, conc_b_3_df,
    df_sto2_A, df_sto2_B, df_sto2_dual,
    output_dir
):
    # --- 1. Set default resampling note ---
    if not resample_note:
        resample_note = "No Resampling"

    # --- 2. Prepare file name & clean output folder ---
    base_filename = filename.split('.')[0] if filename else "output"
    output_path = os.path.join(output_dir, f"{base_filename}_concentrations.xlsx")

    os.makedirs(output_dir, exist_ok=True)
    for file in os.listdir(output_dir):
        file_path = os.path.join(output_dir, file)
        if os.path.isfile(file_path) and file.endswith(".xlsx"):
            os.remove(file_path)

    # --- 3. Build dark signal mapping ---
    signal_dark_dictionary = {
        f'LED_{side}_{wl}_DET{d}': f'LED_{side}_DARK_DET{d}'
        for side in ['A', 'B']
        for wl in ['782', '801', '808', '828', '848', '887']
        for d in [1, 2, 3]
    }

    # --- 4. Helper functions ---
    def calculate_snr(signal_data, dark_data):
        signal = np.mean(signal_data)
        dark_mean = np.mean(dark_data)
        return (signal - dark_mean) / dark_mean if dark_mean != 0 else np.nan

    def calculate_group_snr(group):
        snr_vals = []
        for col in group:
            dark_col = signal_dark_dictionary.get(col)
            if col in df.columns and dark_col in df.columns:
                snr_vals.append(calculate_snr(df[col], df[dark_col]))
        return np.nanmean(snr_vals) if snr_vals else np.nan

    def calculate_nep(dark_cols):
        dark_vals = [df[col].dropna().values for col in dark_cols if col in df.columns]
        return np.std(np.concatenate(dark_vals)) if dark_vals else np.nan

    # --- 5. Define detector groups ---
    group_1 = ['LED_A_782_DET1', 'LED_A_801_DET1', 'LED_A_808_DET1', 'LED_A_828_DET1', 'LED_A_848_DET1', 'LED_A_887_DET1',
               'LED_B_782_DET3', 'LED_B_801_DET3', 'LED_B_808_DET3', 'LED_B_828_DET3', 'LED_B_848_DET3', 'LED_B_887_DET3']
    group_2 = ['LED_A_782_DET2', 'LED_A_801_DET2', 'LED_A_808_DET2', 'LED_A_828_DET2', 'LED_A_848_DET2', 'LED_A_887_DET2',
               'LED_B_782_DET2', 'LED_B_801_DET2', 'LED_B_808_DET2', 'LED_B_828_DET2', 'LED_B_848_DET2', 'LED_B_887_DET2']
    group_3 = ['LED_A_782_DET3', 'LED_A_801_DET3', 'LED_A_808_DET3', 'LED_A_828_DET3', 'LED_A_848_DET3', 'LED_A_887_DET3',
               'LED_B_782_DET1', 'LED_B_801_DET1', 'LED_B_808_DET1', 'LED_B_828_DET1', 'LED_B_848_DET1', 'LED_B_887_DET1']

    snr_1 = calculate_group_snr(group_1)
    snr_2 = calculate_group_snr(group_2)
    snr_3 = calculate_group_snr(group_3)

    nep_1 = calculate_nep(['LED_A_DARK_DET1', 'LED_B_DARK_DET1'])
    nep_2 = calculate_nep(['LED_A_DARK_DET2', 'LED_B_DARK_DET2'])
    nep_3 = calculate_nep(['LED_A_DARK_DET3', 'LED_B_DARK_DET3'])

    # --- 6. Create summary DataFrame ---
    summary_df = pd.DataFrame([
        ["Resampling Method", resample_note],
        ["NEP Detector 1 (mV)", round(nep_1, 4)],
        ["NEP Detector 2 (mV)", round(nep_2, 4)],
        ["NEP Detector 3 (mV)", round(nep_3, 4)],
        ["SNR Short Channel Average", round(snr_1, 4)],
        ["SNR Mid Channel Average", round(snr_2, 4)],
        ["SNR Long Channel Average", round(snr_3, 4)],
    ], columns=["Metric", "Value"])

    # --- 7. Rename concentration & StO₂ columns ---
    conc_a_1_df.columns = ["LED-A_DET-1_HHb", "LED-A_DET-1_HbO2", "LED-A_DET-1_oxCCO"]
    conc_a_2_df.columns = ["LED-A_DET-2_HHb", "LED-A_DET-2_HbO2", "LED-A_DET-2_oxCCO"]
    conc_a_3_df.columns = ["LED-A_DET-3_HHb", "LED-A_DET-3_HbO2", "LED-A_DET-3_oxCCO"]
    conc_b_1_df.columns = ["LED-B_DET-1_HHb", "LED-B_DET-1_HbO2", "LED-B_DET-1_oxCCO"]
    conc_b_2_df.columns = ["LED-B_DET-2_HHb", "LED-B_DET-2_HbO2", "LED-B_DET-2_oxCCO"]
    conc_b_3_df.columns = ["LED-B_DET-3_HHb", "LED-B_DET-3_HbO2", "LED-B_DET-3_oxCCO"]
    df_sto2_A.columns = ["STO2_A"]
    df_sto2_B.columns = ["STO2_B"]
    df_sto2_dual.columns = ["STO2_AB"]

    # --- 8. Combine all data ---
    result_df = pd.concat([
        conc_a_1_df, conc_a_2_df, conc_a_3_df,
        conc_b_1_df, conc_b_2_df, conc_b_3_df,
        df_sto2_A, df_sto2_B, df_sto2_dual
    ], axis=1)

    # Add Date and Time
    result_df.insert(0, "Time", df["Time"].values if "Time" in df.columns else np.nan)
    result_df.insert(0, "Date", pd.Timestamp.now().strftime("%m/%d/%Y"))

    # --- 9. Write to Excel ---
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        summary_df.to_excel(writer, sheet_name='concentration', index=False, startrow=0)
        result_df.to_excel(writer, sheet_name='concentration', index=False, startrow=len(summary_df) + 2)

    return output_path

@app.callback(
    Output("download-conc-xlsx", "data"),
    Input("download_concentrations_excel_btn", "n_clicks"),
    State("concentrations", "data"),  # Use saved data
    prevent_initial_call=True
)
def download_concentration_excel(n_clicks, conc_data):
    if not n_clicks or not conc_data or "excel_path" not in conc_data:
        raise PreventUpdate

    excel_path = conc_data["excel_path"]

    if not os.path.exists(excel_path):
        return html.Div("❌ Excel file not found for download.")

    return dcc.send_file(excel_path)

#=======================Upload to cloud========================================
# Modal visibility toggle
@callback(
    Output('upload-modal', 'style'),
    Input('upload-cloud-button', 'n_clicks'),
    Input('close-modal', 'n_clicks'),
    State('upload-modal', 'style'),
    prevent_initial_call=True
)
def toggle_modal(open_clicks, close_clicks, current_style):
    if ctx.triggered_id == 'upload-cloud-button':
        return {**current_style, 'display': 'flex'}
    elif ctx.triggered_id == 'close-modal':
        return {**current_style, 'display': 'none'}
    return current_style

# Show selected file names
@callback(Output('filename-raw', 'children'), Input('upload-raw', 'filename'))
def show_raw_filename(filename):
    return f"File selected: {filename}" if filename else ""

@callback(Output('filename-concentration', 'children'), Input('upload-concentration', 'filename'))
def show_conc_filename(filename):
    return f"File selected: {filename}" if filename else ""

@callback(Output('filename-ctg', 'children'), Input('upload-ctg', 'filename'))
def show_ctg_filename(filename):
    return f"File selected: {filename}" if filename else ""

# Upload to S3 and show alerts
@callback(
    Output('upload-alerts', 'children'),
    Input('submit-modal', 'n_clicks'),
    State('upload-raw', 'contents'), State('upload-raw', 'filename'),
    State('upload-concentration', 'contents'), State('upload-concentration', 'filename'),
    State('upload-ctg', 'contents'), State('upload-ctg', 'filename'),
    prevent_initial_call=True
)
def upload_files_to_s3(n_clicks, raw_content, raw_filename, conc_content, conc_filename, ctg_content, ctg_filename):
    files = [
        ('upload-raw', raw_content, raw_filename),
        ('upload-concentration', conc_content, conc_filename),
        ('upload-ctg', ctg_content, ctg_filename)
    ]
    alerts = []

    for input_id, content, filename in files:
        if content and filename:
            bucket = bucket_map[input_id]
            try:
                s3.head_object(Bucket=bucket, Key=filename)
                alerts.append(dbc.Alert(f"❌ File '{filename}' already exists in {bucket}", color='danger'))
                continue
            except s3.exceptions.ClientError as e:
                if e.response['Error']['Code'] != '404':
                    alerts.append(dbc.Alert(f"❌ Error checking {filename}: {str(e)}", color='danger'))
                    continue

            try:
                content_type, content_string = content.split(',')
                decoded = base64.b64decode(content_string)
                s3.upload_fileobj(io.BytesIO(decoded), bucket, filename)
                alerts.append(dbc.Alert(f"✅ Uploaded '{filename}' to {bucket}", color='success'))
            except Exception as e:
                alerts.append(dbc.Alert(f"❌ Failed to upload {filename}: {str(e)}", color='danger'))

    return alerts


if __name__ == '__main__':
    app.run(debug=False, port=8052)