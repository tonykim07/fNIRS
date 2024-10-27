import plotly.graph_objects as go
import numpy as np
import networkx as nx

def mesh_properties(mesh_coords):
    """Calculate center and radius of sphere minimally containing a 3-D mesh."""
    radii = []
    center = []

    for coords in mesh_coords:
        c_max = max(c for c in coords)
        c_min = min(c for c in coords)
        center.append((c_max + c_min) / 2)

        radius = (c_max - c_min) / 2
        radii.append(radius)

    return center, max(radii)

def create_plot():
    # Download and prepare dataset from BrainNet repo
    coords = np.loadtxt(np.lib.npyio.DataSource().open('BrainMesh_Ch2_smoothed.nv'), skiprows=1, max_rows=53469)
    x, y, z = coords.T

    triangles = np.loadtxt(np.lib.npyio.DataSource().open('BrainMesh_Ch2_smoothed.nv'), skiprows=53471, dtype=int)
    triangles_zero_offset = triangles - 1
    i, j, k = triangles_zero_offset.T

    # Generate 3D mesh for the brain
    fig = go.Figure(data=[go.Mesh3d(x=x, y=y, z=z,
                                     i=i, j=j, k=k,
                                     color='lightpink', opacity=0.5, name='', showscale=False, hoverinfo='none')])

    # Custom points selection: Select 10 scattered points on the brain surface
    custom_points_indices = np.random.choice(coords.shape[0], 10, replace=False)  # Random 10 points from surface
    custom_points = coords[custom_points_indices]

    # Generate networkx graph with 10 nodes and custom layout with these specific points
    G = nx.Graph()
    G.add_nodes_from(range(10))  # Create 10 nodes

    # Define positions of each node using the custom points
    pos_3d = {node: tuple(custom_points[node]) for node in G.nodes()}

    # Prepare node positions for Plotly scatter3d
    nodes_x = [position[0] for position in pos_3d.values()]
    nodes_y = [position[1] for position in pos_3d.values()]
    nodes_z = [position[2] for position in pos_3d.values()]

    # Define node color
    node_colors = ['red' for _ in range(10)]  # Color all nodes red for visibility

    # Add node plotly trace
    fig.add_trace(go.Scatter3d(x=nodes_x, y=nodes_y, z=nodes_z,
                               mode='markers',
                               name='Custom Nodes',
                               marker=dict(
                                           size=6,
                                           color=node_colors
                                          )
                               ))

    # Make axes invisible
    fig.update_scenes(xaxis_visible=False,
                      yaxis_visible=False,
                      zaxis_visible=False)

    # Manually adjust size of figure
    fig.update_layout(autosize=False,
                      width=800,
                      height=800)

    return fig

# Generate and display the Plotly figure
fig = create_plot()
# Opens in the default browser
fig.show()
