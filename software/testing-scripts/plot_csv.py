"""
plot_csv.py
==================
This script generates static HTML pages for visualizing ADC and mBLL data using Plotly.
It reads data from CSV files (all_groups.csv for ADC, processed_output.csv for mBLL)
and creates interactive plots for each group.
The CSV files should be in the same directory as the script.
"""

import webbrowser
import tempfile
import os
import plotly.graph_objs as go
from plotly.offline import plot
import pandas as pd

def view_static_adc_plotly():
    """
    Generate static HTML for ADC data visualization.
    This function creates a Plotly figure for each group and returns the HTML.
    """
    # Load CSV data.
    # data_dir = 'sample_data' if demo_mode else '.'
    csv_path = 'all_groups.csv'
    df = pd.read_csv(csv_path)

    # Build separate figures for each group.
    figures_html = ""
    for i in range(8):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x = df["Time (s)"],
            y = df[f"G{i}_Short"],
            mode = 'lines',
            name = 'Short'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time (s)"],
            y = df[f"G{i}_Long1"],
            mode = 'lines',
            name = 'Long1'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time (s)"],
            y = df[f"G{i}_Long2"],
            mode = 'lines',
            name = 'Long2'
        ))

        fig.update_layout(
            title = f"Group {i+1}",
            xaxis_title = "Time (s)",
            yaxis_title = "Value",
            autosize=True,
            margin=dict(l=50, r=50, t=50, b=50)
        )

        # Generate an HTML div for this figure without including Plotly.js again.
        div = plot(fig,
                   output_type='div',
                   include_plotlyjs=False,
                   config={'displayModeBar': True,
                           'responsive': True})
        figures_html += f"<div style='margin-bottom:50px;'>{div}</div>"

    # Include Plotly.js only once in the head.
    html = f"""
    <html>
      <head>
         <title>ADC Static Plots</title>
         <meta charset="UTF-8">
         <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
         <style>
           body {{
             margin: 0;
             padding: 20px;
             background-color: #eef2f7;
             font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
           }}
         </style>
      </head>
      <body>
         {figures_html}
      </body>
    </html>
    """
    return html

def view_static_mbll_plotly():
    """
    Load and visualize mBLL data from CSV file.
    This function generates a static HTML page with Plotly figures.
    """
    # Load CSV data
    # data_dir = 'sample_data' if demo_mode else '.'
    csv_path = 'processed_output.csv'
    df = pd.read_csv(csv_path)

    # Build separate figures for each group.
    figures_html = ""
    for i in range(8):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D1_hbo"],
            mode = 'lines',
            name = 'D1_hbo'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D1_hbr"],
            mode = 'lines',
            name = 'D1_hbr'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D2_hbo"],
            mode = 'lines',
            name = 'D2_hbo'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D2_hbr"],
            mode = 'lines',
            name = 'D2_hbr'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D3_hbo"],
            mode = 'lines',
            name = 'D3_hbo'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D3_hbr"],
            mode = 'lines',
            name = 'D3_hbr'
        ))

        fig.update_layout(
            title = f"Group {i+1}",
            xaxis_title = "Time (s)",
            # yaxis_title = "Value",
            autosize=True,
            margin=dict(l=50, r=50, t=50, b=50)
        )

        # Generate an HTML div for this figure without including Plotly.js again.
        div = plot(fig,
                   output_type='div',
                   include_plotlyjs=False,
                   config={'displayModeBar': True, 'responsive': True})
        figures_html += f"<div style='margin-bottom:50px;'>{div}</div>"

    # Include Plotly.js only once in the head.
    html = f"""
    <html>
      <head>
         <title>ADC Static Plots</title>
         <meta charset="UTF-8">
         <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
         <style>
           body {{
             margin: 0;
             padding: 20px;
             background-color: #eef2f7;
             font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
           }}
         </style>
      </head>
      <body>
         {figures_html}
      </body>
    </html>
    """
    return html

def show_html_in_browser(html: str, title: str):
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
        f.write(html)
        file_path = f.name
    print(f"[INFO] Opening {title} plot in browser: {file_path}")
    webbrowser.open(f'file://{file_path}')

# ADC
html = view_static_adc_plotly()
show_html_in_browser(html, "ADC")

# mBLL
html = view_static_mbll_plotly()
show_html_in_browser(html, "mBLL")
