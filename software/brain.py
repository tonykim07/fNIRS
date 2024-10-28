import plotly.graph_objects as go
import numpy as np
import networkx as nx

def generate_activation_data(num_nodes, num_frames):
    """Generate random activation data for each node across timeframes."""
    return np.random.randint(1, 4097, size=(num_nodes, num_frames))

def create_animated_plot():
    # Load and prepare dataset for brain mesh
    coords = np.loadtxt(np.lib.npyio.DataSource().open('BrainMesh_Ch2_smoothed.nv'), skiprows=1, max_rows=53469)
    x, y, z = coords.T

    triangles = np.loadtxt(np.lib.npyio.DataSource().open('BrainMesh_Ch2_smoothed.nv'), skiprows=53471, dtype=int)
    triangles_zero_offset = triangles - 1
    i, j, k = triangles_zero_offset.T

    # Generate 3D mesh for the brain and add it to the figure
    fig = go.Figure(data=[go.Mesh3d(x=x, y=y, z=z,
                                     i=i, j=j, k=k,
                                     color='lightpink', opacity=0.5, name='Brain Mesh', showscale=False, hoverinfo='none')])

    # Custom points selection: Select 30 scattered points on the brain surface
    num_nodes = 30
    custom_points_indices = np.random.choice(coords.shape[0], num_nodes, replace=False)
    custom_points = coords[custom_points_indices]

    # Generate networkx graph with nodes and custom layout
    G = nx.Graph()
    G.add_nodes_from(range(num_nodes))

    # Define 3D positions for each node
    pos_3d = {node: tuple(custom_points[node]) for node in G.nodes()}

    # Generate random activation data
    num_frames = 50  # Number of timeframes
    activation_data = generate_activation_data(num_nodes, num_frames)

    # Prepare node positions
    nodes_x = [position[0] for position in pos_3d.values()]
    nodes_y = [position[1] for position in pos_3d.values()]
    nodes_z = [position[2] for position in pos_3d.values()]

    # Add traces for animation frames
    frames = []
    for t in range(num_frames):
        # Get current activations and map to color scale
        activations = activation_data[:, t]
        colors = [f"rgb({int(255 * a / 4096)}, 0, {255 - int(255 * a / 4096)})" for a in activations]  # red-blue gradient

        # Create frame trace for the current timeframe with both mesh and nodes
        frame = go.Frame(data=[
            go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color='lightpink', opacity=0.5, name='Brain Mesh', showscale=False, hoverinfo='none'),
            go.Scatter3d(x=nodes_x, y=nodes_y, z=nodes_z, mode='markers', marker=dict(size=6, color=colors), name=f'Time {t}')
        ])
        frames.append(frame)

    # Initial color (first timeframe)
    initial_colors = [f"rgb({int(255 * a / 4096)}, 0, {255 - int(255 * a / 4096)})" for a in activation_data[:, 0]]
    
    # Add the scatter trace for initial state
    fig.add_trace(go.Scatter3d(x=nodes_x, y=nodes_y, z=nodes_z,
                               mode='markers',
                               marker=dict(size=6, color=initial_colors),
                               name='Sensor Nodes'))

    # Make axes invisible
    fig.update_scenes(xaxis_visible=False, yaxis_visible=False, zaxis_visible=False)

    # Update layout for animation with smooth transitions
    fig.update_layout(
        autosize=False, width=800, height=800,
        updatemenus=[dict(type='buttons', showactive=False,
                          buttons=[dict(label='Play', method='animate',
                                        args=[None, dict(frame=dict(duration=200, redraw=True),
                                                         fromcurrent=True,
                                                         transition=dict(duration=200, easing="linear"))])])],
        title="3D Brain Mesh with Sensor Activation Over Time"
    )

    # Add frames to figure
    fig.frames = frames

    return fig

# Generate and display the animated Plotly figure
fig = create_animated_plot()
fig.show()
