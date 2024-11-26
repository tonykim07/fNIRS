from dash import Dash, html, dcc
from scipy.spatial import cKDTree
import plotly.graph_objects as go
import numpy as np
import nibabel as nib

# Load the AAL mapping
def load_aal_mapping(aal_file):
    aal_img = nib.load(aal_file)
    aal_data = aal_img.get_fdata()
    return aal_data, aal_img.affine

# Filter coordinates by proximity to the brain surface
def filter_coordinates_to_surface(coords, surface_coords, threshold=2.0):
    tree = cKDTree(surface_coords)
    distances, _ = tree.query(coords)
    return coords[distances <= threshold]

# Generate random activation data
def generate_activation_data(num_nodes, num_frames):
    return np.random.randint(0, 5000, size=(num_nodes, num_frames))

# Map points to regions based on their voxel positions
def map_points_to_regions(points, affine, aal_data):
    voxel_coords = np.round(np.linalg.inv(affine) @ np.column_stack((points, np.ones(points.shape[0]))).T).T[:, :3]
    voxel_coords = voxel_coords.astype(int)
    regions = []
    for voxel in voxel_coords:
        if (0 <= voxel[0] < aal_data.shape[0] and
            0 <= voxel[1] < aal_data.shape[1] and
            0 <= voxel[2] < aal_data.shape[2]):
            regions.append(aal_data[tuple(voxel)])
        else:
            regions.append(-1)  # Mark as invalid
    return np.array(regions)

# Combine everything into a brain mesh plot function
def create_brain_mesh_with_dynamic_highlight(aal_file, activation_threshold=3000):
    # Load and prepare dataset for brain mesh
    coords = np.loadtxt(np.lib.npyio.DataSource().open('BrainMesh_Ch2_smoothed.nv'), skiprows=1, max_rows=53469)
    x, y, z = coords.T

    triangles = np.loadtxt(np.lib.npyio.DataSource().open('BrainMesh_Ch2_smoothed.nv'), skiprows=53471, dtype=int)
    triangles_zero_offset = triangles - 1
    i, j, k = triangles_zero_offset.T

    # Load AAL mapping and affine transformation
    aal_data, affine = load_aal_mapping(aal_file)

    # Generate random sensor nodes and activation data
    num_nodes = 15
    custom_points_indices = np.random.choice(coords.shape[0], num_nodes, replace=False)
    custom_points = coords[custom_points_indices]
    activation_data = generate_activation_data(num_nodes, num_frames=50)
    initial_activations = activation_data[:, 0]

    # Map nodes to regions
    regions = map_points_to_regions(custom_points, affine, aal_data)

    # Find regions to highlight
    highlighted_regions = np.unique(regions[initial_activations > activation_threshold])

    # Filter region coordinates for highlighting
    surface_coords = np.column_stack((x, y, z))
    highlighted_coords = []
    for region in highlighted_regions:
        if region <= 0:  # Skip invalid regions
            continue
        region_mask = aal_data == region
        region_voxels = np.argwhere(region_mask)
        region_world_coords = nib.affines.apply_affine(affine, region_voxels)
        filtered_coords = filter_coordinates_to_surface(region_world_coords, surface_coords, threshold=2.0)
        highlighted_coords.append(filtered_coords)
    highlighted_coords = np.vstack(highlighted_coords) if highlighted_coords else np.empty((0, 3))

    # Create a 3D brain mesh plot
    fig = go.Figure()

    # Add 3D mesh trace
    fig.add_trace(go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        color='lightpink', opacity=0.5, name='Brain Mesh', showscale=False
    ))

    # Add scatter trace for sensor nodes
    fig.add_trace(go.Scatter3d(
        x=custom_points[:, 0], 
        y=custom_points[:, 1], 
        z=custom_points[:, 2],
        mode='markers',
        marker=dict(
            size=6,
            color=initial_activations,
            colorscale='RdBu_r',  # Reversed color scale (Blue -> Red)
            colorbar=dict(
                title="Activation Level",
                x=0.0,  # Position colorbar on the left
                xanchor='left',
                tickvals=[0, 1000, 2000, 3000, 4000, 5000],
                ticktext=['0', '1000', '2000', '3000', '4000', '5000']
            )
        ),
        name='Sensor Nodes'
    ))

    # Add scatter trace for highlighted regions
    if highlighted_coords.size > 0:
        fig.add_trace(go.Scatter3d(
            x=highlighted_coords[:, 0], 
            y=highlighted_coords[:, 1], 
            z=highlighted_coords[:, 2],
            mode='markers',
            marker=dict(
                size=2,
                color='red',
                opacity=0.8
            ),
            name='Highlighted Regions'
        ))

    fig.update_layout(
        title=f"3D Brain Mesh with Dynamic Region Highlighting (Threshold: {activation_threshold})",
        scene=dict(xaxis_visible=False, yaxis_visible=False, zaxis_visible=False),
        width=800,
        height=800
    )
    return fig


# Define the stacked activation plot function
def create_stacked_activation_plot(activation_data, num_nodes, num_frames):
    fig = go.Figure()
    offset = 5000

    for node in range(num_nodes):
        fig.add_trace(go.Scatter(
            x=np.arange(num_frames),
            y=activation_data[node, :] + node * offset,
            mode='lines+markers',
            name=f"Node {node}",
            line=dict(width=2),
            marker=dict(size=6)
        ))

    fig.update_yaxes(
        title_text="Activation Level (Stacked)",
        tickmode="array",
        tickvals=[node * offset + offset / 2 for node in range(num_nodes)],
        ticktext=[f"Node {node}" for node in range(num_nodes)]
    )
    fig.update_xaxes(title_text="Time (frames)")

    fig.update_layout(
        title="Node Activation Over Time",
        height=800,
        width=600,
        showlegend=True
    )

    return fig

# Generate random activation data
activation_data = generate_activation_data(num_nodes=25, num_frames=50)

# Create the figures
aal_file = 'aal.nii'  # Path to your AAL file
brain_mesh_fig = create_brain_mesh_with_dynamic_highlight(aal_file, activation_threshold=3000)
brain_mesh_fig.show()
stacked_fig = create_stacked_activation_plot(activation_data, num_nodes=25, num_frames=50)

# Build Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        dcc.Graph(figure=brain_mesh_fig, style={'display': 'inline-block'}),
        dcc.Graph(figure=stacked_fig, style={'display': 'inline-block'})
    ], style={'display': 'flex', 'justify-content': 'center'})
])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False, port=8050)
