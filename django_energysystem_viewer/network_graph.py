import igraph as ig
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import List, Tuple, Dict, Set

def generate_Graph(
        updated_process_set: pd.DataFrame,
        selected_sectors: List[str],
        algorithm: str,
        separate_commodities: str,
        process_specific: str,
        commodity_specific: str,
        nomenclature_level: int,
) -> go.Figure:
    """
    Generate a Plotly graph for the selected sectors and algorithm.

    Parameters:
    updated_process_set (pd.DataFrame): The updated process set from the Excel file.
    selected_sectors (List[str]): The selected sectors for filtering the process set.
    algorithm (str): The selected algorithm for generating the layout.
    separate_commodities (str): Option to separate or aggregate commodities.
    process_specific (str): The selected process to generate the graph for.
    commodity_specific (str): The selected commodity to generate the graph for.

    Returns:
    go.Figure: The generated graph.
    """
    axis = dict(
        showbackground=False,
        showline=False,
        zeroline=False,
        showgrid=False,
        showticklabels=False,
        title="",
        showspikes=False,
        visible=True,
    )

    graph_layout = go.Layout(
        autosize=True,
        height=800,
        width=1000,
        showlegend=True,
        hovermode="closest",
        hoverdistance=10,
        spikedistance=-1,
        scene=dict(
            xaxis=dict(axis),
            yaxis=dict(axis),
        ),
        margin=dict(l=0, r=0, t=0, b=0, autoexpand=True),
    )

    fig = go.Figure(layout=graph_layout)

    if not process_specific and not commodity_specific:
        if separate_commodities == "sep":
            traces = generate_trace(updated_process_set, selected_sectors, algorithm, "sep", nomenclature_level)
            fig.add_traces(traces)
        elif separate_commodities == "agg":
            traces = generate_trace(updated_process_set, selected_sectors, algorithm, "agg", nomenclature_level)
            fig.add_traces(traces)
    elif process_specific:
        traces = generate_trace_process_specific(updated_process_set, process_specific)
        fig.add_traces(traces)
    elif commodity_specific:
        traces = generate_trace_commodity_specific(updated_process_set, commodity_specific, selected_sectors)
        fig.add_traces(traces)

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    predefined_order = ["edges", "pow", "x2x", "hea", "ind", "tra", "pri", "sec", "iip", "exo"]
    fig = update_layout_with_unique_legend(fig, predefined_order)
    # Update the layout for the legend position
    fig.update_layout(legend=dict(y=0.5, yanchor="middle"))

    return fig  # Return the figure to be rendered later

def generate_trace(process_set: pd.DataFrame, selected_sectors: list, algorithm: str, separate_commodities: str, nomenclature_level: int) -> List[go.Scatter]:
    """
    Generate Plotly traces for nodes and edges.

    Parameters:
    process_set (pd.DataFrame): The updated process set from the Excel file.
    sector (str): The selected sector for filtering the process set.
    algorithm (str): The selected algorithm for generating the layout.
    separate_commodities (str): Option to separate or aggregate commodities.

    Returns:
    List[go.Scatter]: Combined trace of nodes and edges including their colors and shapes.
    """
    process_set['process_trimmed'] = process_set['process'].apply(lambda x: '_'.join(x.split('_')[:nomenclature_level]))
    process_set_grouped = process_set.groupby('process_trimmed').agg({
        'input': lambda x: ','.join(map(str, filter(pd.notna, x))),
        'output': lambda x: ','.join(map(str, filter(pd.notna, x)))
    }).reset_index()
    process_set_grouped.rename(columns={'process_trimmed': 'process'}, inplace=True)
    # Remove duplicate inputs/outputs after the grouping
    process_set_grouped['input'] = process_set_grouped['input'].apply(lambda x: ','.join(sorted(set(x.split(',')))) if pd.notna(x) else x)
    process_set_grouped['output'] = process_set_grouped['output'].apply(lambda x: ','.join(sorted(set(x.split(',')))) if pd.notna(x) else x)

    inputs, outputs, processes = get_filtered_process_data(process_set_grouped, selected_sectors)

    # Get node connections
    nodes, edges, node_connections = create_nodes_and_edges(inputs, outputs, processes)
    G = ig.Graph(edges)
    layout = generate_layout(G, algorithm)

    labels, node_colors, node_shapes = get_node_attributes(nodes, processes)
    Xn, Yn = get_node_coordinates(layout, len(nodes), 0, 0)
    Xe_list, Ye_list = get_edge_coordinates_list(layout, edges, 0, 0)

    # Create edge traces with customdata
    edge_traces = create_edge_traces(Xe_list, Ye_list, edges, nodes)
    # Include node_connections
    node_traces = create_node_traces_by_color(Xn, Yn, labels, node_shapes, node_colors, processes, node_connections)

    return edge_traces + node_traces

def get_filtered_process_data(process_set: pd.DataFrame, selected_sectors: list) -> Tuple[
    List[str], List[str], List[str]]:
    """
    Get filtered process data based on the provided filter type and value.

    Parameters:
    process_set (pd.DataFrame): The process set DataFrame.
    filter_value (str): The value to filter by.
    filter_type (str): The type of filter ('sector', 'process').

    Returns:
    Tuple[List[str], List[str], List[str]]: Lists of inputs, outputs, and processes.
    """
    sector_abbrvs = ["pow", "x2x", "ind", "tra", "hea", "hel"]
    filtered_set = pd.DataFrame()
    for sector_abbrv in sector_abbrvs:
        if sector_abbrv in selected_sectors:
            filtered_set = pd.concat(
                [filtered_set, process_set[process_set["process"].str.startswith(sector_abbrv)]])
    inputs = filtered_set["input"].tolist()
    outputs = filtered_set["output"].tolist()
    processes = filtered_set["process"].tolist()

    return inputs, outputs, processes

def create_nodes_and_edges(inputs: List[str], outputs: List[str], processes: List[str]) -> Tuple[
    List[str], List[Tuple[int, int]], Dict[str, Dict[str, List[int]]]]:
    """
    Create nodes and edges from inputs, outputs, and processes.
    """
    nodes = []
    edges = []
    node_connections = {}  # Key: node_id, Value: {'edges': [edge_indices], 'nodes': [connected_node_ids]}

    for i in range(len(processes)):
        input_list = inputs[i].split(",") if isinstance(inputs[i], str) else []
        input_list = [item.strip().replace("[", "").replace("]", "") for item in input_list]
        input_list = [item.strip().replace("_orig", "") for item in input_list]
        input_list = [commodity for commodity in input_list if isinstance(commodity, str) and not commodity.startswith('emi')]

        output_list = outputs[i].split(",") if isinstance(outputs[i], str) else []
        output_list = [item.strip().replace("[", "").replace("]", "") for item in output_list]
        output_list = [item.strip().replace("_orig", "") for item in output_list]
        output_list = [commodity for commodity in output_list if isinstance(commodity, str) and not commodity.startswith('emi')]

        process_list = processes[i].split(",") if isinstance(processes[i], str) else []
        process_list = [item.strip().replace("[", "").replace("]", "") for item in process_list]

        input_list = [input_node for input_node in input_list if input_node != '']
        output_list = [output_node for output_node in output_list if output_node != '']

        for input_node in input_list:
            if input_node not in nodes:
                nodes.append(input_node)
            source_index = nodes.index(input_node)
            source_node_id = nodes[source_index]

            for process_node in process_list:
                if process_node not in nodes:
                    nodes.append(process_node)
                target_index = nodes.index(process_node)
                target_node_id = nodes[target_index]

                edge_index = len(edges)
                edges.append((source_index, target_index))

                # Update node_connections for source_node_id
                node_connections.setdefault(source_node_id, {'edges': [], 'nodes': []})
                node_connections[source_node_id]['edges'].append(edge_index)
                node_connections[source_node_id]['nodes'].append(target_node_id)

                # Update node_connections for target_node_id
                node_connections.setdefault(target_node_id, {'edges': [], 'nodes': []})
                node_connections[target_node_id]['edges'].append(edge_index)
                node_connections[target_node_id]['nodes'].append(source_node_id)

        for process_node in process_list:
            if process_node not in nodes:
                nodes.append(process_node)
            source_index = nodes.index(process_node)
            source_node_id = nodes[source_index]

            for output_node in output_list:
                if output_node not in nodes:
                    nodes.append(output_node)
                target_index = nodes.index(output_node)
                target_node_id = nodes[target_index]

                edge_index = len(edges)
                edges.append((source_index, target_index))

                # Update node_connections for source_node_id
                node_connections.setdefault(source_node_id, {'edges': [], 'nodes': []})
                node_connections[source_node_id]['edges'].append(edge_index)
                node_connections[source_node_id]['nodes'].append(target_node_id)

                # Update node_connections for target_node_id
                node_connections.setdefault(target_node_id, {'edges': [], 'nodes': []})
                node_connections[target_node_id]['edges'].append(edge_index)
                node_connections[target_node_id]['nodes'].append(source_node_id)

    return nodes, edges, node_connections

def generate_layout(G: ig.Graph, algorithm: str) -> ig.Layout:
    """
    Generate the layout for the graph according to the selected algorithm.

    Parameters:
    G (ig.Graph): The graph for generating the layout.
    algorithm (str): The selected algorithm for generating the layout.

    Returns:
    ig.Layout: The generated layout.
    """
    # Rejected layout algorithms
    # “drl”: G.layout_drl, # very bundled, not clear
    # “mds”: G.layout_mds, # cornered, not clear
    # "lgl": G.layout_lgl, # two-dimensional connection
    # "umap": G.layout_umap, # not working properly
    # "dav": G.layout_davidson_harel, # not working properly

    layout_mapping_with_dim = {
        "kk": G.layout_kamada_kawai,  #1 clear centrality, radial edges
        "fr": G.layout_fruchterman_reingold,  #2 clear centrality,
    }
    layout_mapping_without_dim = {
        "go": G.layout_graphopt, #3 fast, very distributed and less sorted nodes
    }
    if algorithm in layout_mapping_with_dim:
        return layout_mapping_with_dim[algorithm](dim=2)
    elif algorithm in layout_mapping_without_dim:
        return layout_mapping_without_dim[algorithm]()

def get_node_attributes(nodes: List[str], processes: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """
    Get node attributes including labels, colors, and shapes.

    Parameters:
    nodes (List[str]): List of nodes.
    processes (List[str]): List of processes.

    Returns:
    Tuple[List[str], List[str], List[str]]: Node labels, colors, and shapes.
    """
    labels, node_colors, node_shapes = [], [], []
    for node in nodes:
        labels.append(node)
        node_colors.append(assign_color(node, processes))
        node_shapes.append(assign_shape(node, processes))

    return labels, node_colors, node_shapes

def assign_color(node: str, processes: List[str]) -> str:
    """
    Assign a color to each node based on its sector or type.

    Parameters:
    node (str): The node to assign a color to.
    processes (List[str]): The list of processes for reference.

    Returns:
    str: The assigned color of the node.
    """
    if node in processes:
        sector_colors = {
            "pow": "rgb(255, 255, 0)",  # Yellow
            "x2x": "rgb(0, 0, 255)",  # Blue
            "ind": "rgb(255, 0, 255)",  # Magenta
            "tra": "#17cda6",  # Turquoise
            "hea": "rgb(255, 0, 0)",  # Red
            "hel": "rgb(0, 0, 0)",  # Black
        }
        sector = node[:3]  # Extract the first three letters of the node name
        return sector_colors.get(sector, "rgb(128, 128, 128)")  # Default color for other sectors
    else:
        source_colors = {
            "pri": "#FFFFFF",  # White
            "sec": "#6aa84f",  # Green
            "exo": "#ED7D31",  # Orange
            "iip": "#9999CC",  # Violet
        }
        source = node[:3]  # Extract the first three letters of the node name
        return source_colors.get(source, "rgb(128, 128, 128)")  # Default color if not found

def assign_shape(node: str, processes: List[str]) -> str:
    """
    Assign a shape to each node based on whether it is a process or an input/output.

    Parameters:
    node (str): The node to assign a shape to.
    processes (List[str]): The list of processes for reference.

    Returns:
    str: The assigned shape of the node.
    """
    return "square" if node in processes else "circle"

def get_node_coordinates(layout: ig.Layout, num_nodes: int, x_offset: int, y_offset: int) -> Tuple[
    List[float], List[float]]:
    """
    Get coordinates for nodes with the given layout and offsets.

    Parameters:
    layout (ig.Layout): The layout of the nodes.
    num_nodes (int): The number of nodes.
    x_offset (int): The x offset for the nodes.
    y_offset (int): The y offset for the nodes.

    Returns:
    Tuple[List[float], List[float]]: X and Y coordinates of nodes.
    """
    Xn, Yn = [], []
    for k in range(num_nodes):
        Xn.append(layout[k][0] + x_offset)
        Yn.append(layout[k][1] + y_offset)
    return Xn, Yn

def get_edge_coordinates_list(layout: ig.Layout, edges: List[Tuple[int, int]], x_offset: int, y_offset: int) -> Tuple[
    List[List[float]], List[List[float]]]:
    """
    Get coordinates for edges with the given layout and offsets.

    Parameters:
    layout (ig.Layout): The layout of the nodes.
    edges (List[Tuple[int, int]]): The list of edges.
    x_offset (int): The x offset for the edges.
    y_offset (int): The y offset for the edges.

    Returns:
    Tuple[List[float], List[float]]: X and Y coordinates of edges.
    """
    Xe_list, Ye_list = [], []
    for e in edges:
        Xe_list.append([layout[e[0]][0] + x_offset, layout[e[1]][0] + x_offset, None])
        Ye_list.append([layout[e[0]][1] + y_offset, layout[e[1]][1] + y_offset, None])
    return Xe_list, Ye_list

def create_edge_traces(Xe_list: List[List[float]], Ye_list: List[List[float]], edges: List[Tuple[int, int]], nodes: List[str]) -> List[go.Scattergl]:
    """
    Create Plotly traces for edges with customdata, using scattergl for performance.
    """
    edge_traces = []
    num_edges = len(edges)
    for i in range(num_edges):
        x_coords = Xe_list[i]
        y_coords = Ye_list[i]
        source_index = edges[i][0]
        target_index = edges[i][1]
        source_node_id = nodes[source_index]
        target_node_id = nodes[target_index]

        # Customdata needs to match the number of points (including None)
        customdata = [
            {'edge_index': i, 'source': source_node_id, 'target': target_node_id},
            {'edge_index': i, 'source': source_node_id, 'target': target_node_id},
            None  # For the None separator
        ]

        edge_trace = go.Scattergl(
            x=x_coords,
            y=y_coords,
            mode='lines',
            line=dict(color='rgb(160,160,160)', width=0.5, dash='dot'),
            hoverinfo='none',
            customdata=customdata,
            showlegend=False,
            name='edge_{}'.format(i)
        )
        edge_traces.append(edge_trace)

    return edge_traces

def create_node_traces_by_color(Xn: List[float], Yn: List[float], labels: List[str], shapes: List[str],
                                colors: List[str], processes: List[str], node_connections: Dict[str, Dict[str, List[int]]],
                                sizes: List[int] = None, mode: str = "markers") -> List[go.Scattergl]:
    """
    Create Plotly traces for nodes, differentiating by color.

    Parameters:
    Xn (List[float]): X coordinates of nodes.
    Yn (List[float]): Y coordinates of nodes.
    labels (List[str]): Labels for the nodes.
    shapes (List[str]): Shapes of the nodes.
    colors (List[str]): Colors of the nodes.
    processes (List[str]): List of processes.
    sizes (List[int], optional): Sizes of the nodes. Defaults to None.
    mode (str, optional): Mode for the trace. Defaults to "markers".

    Returns:
    List[go.Scatter]: List of node traces.
    """
    unique_colors = list(set(colors))
    node_traces = []
    legend_added = set()

    for color in unique_colors:
        indices = [i for i, c in enumerate(colors) if c == color]
        trace_Xn = [Xn[i] for i in indices]
        trace_Yn = [Yn[i] for i in indices]
        trace_labels = [labels[i] for i in indices]
        trace_shapes = [shapes[i] for i in indices]

        customdata = []
        for idx in indices:
            node_id = labels[idx]
            connected_nodes = node_connections.get(node_id, {}).get('nodes', [])
            connected_edges = node_connections.get(node_id, {}).get('edges', [])
            customdata.append({
                'node_id': node_id,
                'connected_nodes': connected_nodes,
                'connected_edges': connected_edges
            })

        legend_name = trace_labels[0][:3]
        legend_entry = (legend_name, color)

        if legend_entry not in legend_added:
            show_legend = True
            legend_added.add(legend_entry)
        else:
            show_legend = False

        node_trace = go.Scattergl(
            x=trace_Xn,
            y=trace_Yn,
            mode=mode,
            name=legend_name,
            marker=dict(
                symbol=trace_shapes,
                size=8,
                color=color,
                line=dict(color="rgb(50,50,50)", width=0.5),
            ),
            text=trace_labels,
            hoverinfo="text",
            customdata=customdata,
            showlegend=show_legend,
            legendgroup=legend_name
        )
        node_traces.append(node_trace)

    return node_traces

def update_layout_with_unique_legend(fig: go.Figure, predefined_order: List[str]) -> go.Figure:
    """
    Update the layout of the Plotly figure to ensure unique legend entries and reorder them.

    Parameters:
    fig (go.Figure): The Plotly figure.
    predefined_order (List[str]): The predefined order of legend names.

    Returns:
    go.Figure: The updated Plotly figure with unique and ordered legend entries.
    """
    legend_added = set()
    ordered_traces = []

    # Create a dictionary to sort traces based on predefined order
    trace_dict = {name: [] for name in predefined_order}

    # Populate the trace dictionary
    for trace in fig.data:
        if trace.name in trace_dict:
            trace_dict[trace.name].append(trace)
        else:
            trace_dict.setdefault(trace.name, []).append(trace)

    # Add traces to ordered_traces based on predefined order
    for name in predefined_order:
        for trace in trace_dict.get(name, []):
            legend_entry = (trace.name, trace.marker.color) if hasattr(trace, 'marker') else (trace.name, None)
            if legend_entry not in legend_added:
                trace.showlegend = True
                legend_added.add(legend_entry)
            else:
                trace.showlegend = False
            ordered_traces.append(trace)

    # Add remaining traces not in predefined order
    for name, traces in trace_dict.items():
        if name not in predefined_order:
            for trace in traces:
                legend_entry = (trace.name, trace.marker.color) if hasattr(trace, 'marker') else (trace.name, None)
                if legend_entry not in legend_added:
                    trace.showlegend = False
                    legend_added.add(legend_entry)
                else:
                    trace.showlegend = False
                ordered_traces.append(trace)

    # Clear existing traces and add ordered traces
    fig.data = []
    for trace in ordered_traces:
        fig.add_trace(trace)

    return fig

def generate_trace_process_specific(updated_process_set: pd.DataFrame, process_name: str) -> List[go.Scatter]:
    """
    Generates the trace for the selected process.

    Parameters
    ----------
    process_name: str
        The selected process, which is used to filter the process set.
    updated_process_set: pd.DataFrame
        The DataFrame containing the process set.

    Returns
    -------
    list
        The combined trace of nodes and edges, including their colors and shapes.
    """
    # Filter the process set for the specific process
    process_set = updated_process_set[updated_process_set['process'] == process_name]
    inputs = process_set['input'].tolist()
    outputs = process_set['output'].tolist()
    processes = process_set['process'].tolist()

    # Create nodes and edges
    nodes, edges, node_connections = create_nodes_and_edges(inputs, outputs, processes)
    G = ig.Graph(edges)
    layout = generate_layout(G, 'fr')  # Using 'fr' as default layout algorithm

    labels, node_colors, node_shapes = get_node_attributes(nodes, processes)
    Xn, Yn = get_node_coordinates(layout, len(nodes), 0, 0)
    Xe_list, Ye_list = get_edge_coordinates_list(layout, edges, 0, 0)

    # Create edge traces with customdata
    edge_traces = create_edge_traces(Xe_list, Ye_list, edges, nodes)
    # Create node traces with customdata
    node_traces = create_node_traces_by_color(Xn, Yn, labels, node_shapes, node_colors, processes, node_connections)

    return edge_traces + node_traces

def generate_trace_commodity_specific(updated_process_set: pd.DataFrame, commodity_name: str, selected_sectors: List[str]) -> List[go.Scatter]:
    """
    Generate Plotly traces for a specific commodity.
    """
    # Filter the process set for the specific commodity
    # We need to find all processes that have the commodity as input or output
    mask = updated_process_set['input'].str.contains(commodity_name, na=False) | updated_process_set['output'].str.contains(commodity_name, na=False)
    process_set = updated_process_set[mask]

    # Apply sector filtering
    process_set = process_set[process_set['process'].str[:3].isin(selected_sectors)]

    inputs = process_set['input'].tolist()
    outputs = process_set['output'].tolist()
    processes = process_set['process'].tolist()

    # Create nodes and edges
    nodes, edges, node_connections = create_nodes_and_edges(inputs, outputs, processes)
    G = ig.Graph(edges)
    layout = generate_layout(G, 'fr')  # Using 'fr' as default layout algorithm

    labels, node_colors, node_shapes = get_node_attributes(nodes, processes)
    Xn, Yn = get_node_coordinates(layout, len(nodes), 0, 0)
    Xe_list, Ye_list = get_edge_coordinates_list(layout, edges, 0, 0)

    # Create edge traces with customdata
    edge_traces = create_edge_traces(Xe_list, Ye_list, edges, nodes)
    # Create node traces with customdata
    node_traces = create_node_traces_by_color(Xn, Yn, labels, node_shapes, node_colors, processes, node_connections)

    return edge_traces + node_traces
