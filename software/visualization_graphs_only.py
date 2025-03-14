from flask import Flask, render_template, jsonify, send_from_directory, request
from flask_socketio import SocketIO
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import numpy as np
import nibabel as nib
from scipy.spatial import cKDTree
import logging
from data_handler import get_latest_data, sio

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
socketio = SocketIO(app)

# Initialize emitter states (all ON by default)
emitter_states = [True] * 16

# Initialize control data
control_data = {
    'emitter_control_override_enable': 0,
    'emitter_control_state': 0,
    'emitter_pwm_control_h': 0,
    'emitter_pwm_control_l': 0,
    'mux_control_override_enable': 0,
    'mux_control_state': 0
}

def filter_coordinates_to_surface(coords, surface_coords, threshold=2.0):
    """ 
    Filter coordinates by proximity to the brain surface.
    """
    tree = cKDTree(surface_coords)
    distances, _ = tree.query(coords)
    return coords[distances <= threshold]


def create_grouped_activation_plot(activation_data):
    """
    Create a stacked plot with 8 subplots.
    
    activation_data: NumPy array with shape (48, num_timeframes)
      It is assumed that the 48 rows represent 8 groups (each group 6 channels).
    
    For each group, plot the 6 channels as individual time-series with custom colors.
    """
    num_frames = activation_data.shape[1]
    time = np.arange(num_frames)
    num_groups = 8  # since 48/6 = 8
    
    # Define the colors for the 6 channels in order:
    # 'D1, hbo' (dark blue), 'D1, hbr' (light blue), 
    # 'D2, hbo' (dark green), 'D2, hbr' (light green),
    # 'D3, hbo' (dark red), 'D3, hbr' (light red)
    channel_colors = ["darkblue", "lightblue", "darkgreen", "lightgreen", "darkred", "lightcoral"]
    
    # Create subplots with titles for each group.
    fig = make_subplots(
        rows=num_groups, cols=1, shared_xaxes=True, vertical_spacing=0.02,
        subplot_titles=[f"Sensor Group {i+1}" for i in range(num_groups)]
    )
    
    for group in range(num_groups):
        # Extract the 6 channels for this group.
        group_data = activation_data[group*6:(group+1)*6, :]
        for channel in range(6):
            color = channel_colors[channel]
            # Determine the detector and modality based on the channel index.
            detector = f"D{channel//2 + 1}"
            modality = "hbo" if channel % 2 == 0 else "hbr"
            trace_name = f"{detector}, {modality}"
            fig.add_trace(
                go.Scatter(
                    x=time,
                    y=group_data[channel, :],
                    mode='lines+markers',
                    name=trace_name,
                    line=dict(color=color),
                    marker=dict(color=color),
                    showlegend=True  # Enable legend for every group
                ),
                row=group+1, col=1
            )
        # Set y-axis label for each subplot.
        fig.update_yaxes(title_text="Concentration (M)", row=group+1, col=1)
    
    # Set x-axis label on the bottom subplot.
    fig.update_xaxes(title_text="Timeframe", row=num_groups, col=1)
    
    fig.update_layout(
        title="Grouped Activation Data (8 groups, 6 channels each)",
        height=300 * num_groups,  # adjust height per group as needed
        showlegend=True
    )
    return fig


# Define the stacked activation plot function
def create_single_group_plot(activation_data, group_index):
    """
    Create a Plotly figure for a single sensor group.
    
    Parameters:
      activation_data: NumPy array with shape (48, num_timeframes)
      group_index: integer from 0 to 7 indicating which group (each group = 6 rows)
    
    Returns:
      A Plotly figure with:
        - Title "Sensor Group X"
        - x-axis labeled "Timeframe"
        - y-axis labeled "Concentration (M)"
        - 6 traces with custom colors and a separate legend.
    """
    num_frames = activation_data.shape[1]
    time = np.arange(num_frames)
    
    # Colors for the 6 channels in order:
    # 'D1, hbo' (dark blue), 'D1, hbr' (light blue),
    # 'D2, hbo' (dark green), 'D2, hbr' (light green),
    # 'D3, hbo' (dark red), 'D3, hbr' (light red)
    channel_colors = ["darkblue", "lightblue", "darkgreen", "lightgreen", "darkred", "lightcoral"]
    
    # Extract data for the specific sensor group
    group_data = activation_data[group_index*6:(group_index+1)*6, :]
    
    fig = go.Figure()
    for channel in range(6):
        color = channel_colors[channel]
        # Derive the detector and modality names:
        detector = f"D{channel//2 + 1}"
        modality = "hbo" if channel % 2 == 0 else "hbr"
        trace_name = f"{detector}, {modality}"
        fig.add_trace(go.Scatter(
            x=time,
            y=group_data[channel, :],
            mode='lines+markers',
            name=trace_name,
            line=dict(color=color),
            marker=dict(color=color)
        ))
    
    # Set the layout with title and axis labels
    fig.update_layout(
        title=f"Sensor Group {group_index+1}",
        xaxis_title="Timeframe",
        yaxis_title="Concentration (M)",
        showlegend=True
    )
    return fig


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/data')
def data():
    latest_data = get_latest_data()
    if latest_data is None:
        return jsonify({'data': []})
    return jsonify({'data': latest_data.tolist()})

@app.route('/update_graphs')
def update_graphs():
    # print("Updating graphs...")
    latest_data = get_latest_data()
    if latest_data is None:
        return jsonify({'brain_mesh': None, 'stacked_activation': None})

    # Convert stored data back into a NumPy array
    activation_data = np.array(latest_data)
    if activation_data.ndim == 1:
        activation_data = activation_data.reshape(-1, 1)

    num_nodes, num_frames = activation_data.shape

    # Create one figure per sensor group (8 groups total)
    grouped_activation = {}
    for group_index in range(8):
        grouped_activation[f"group{group_index+1}"] = create_single_group_plot(activation_data, group_index).to_json()
    
    return jsonify({'grouped_activation': grouped_activation})


@app.route('/update_emitter_states', methods=['POST'])
def update_emitter_states():
    global emitter_states
    data = request.json
    emitter_states = data['emitter_states']
    return jsonify({'status': 'success'})

@app.route('/update_control_data', methods=['POST'])
def update_control_data():
    global control_data
    data = request.json
    control_data.update(data)
    logging.info(f"Control data updated: {control_data}")
    # Here you would add the code to communicate with the firmware
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    sio.connect('http://localhost:5000', transports=['websocket'])
    socketio.run(app, debug=True, use_reloader=False, port=8050)