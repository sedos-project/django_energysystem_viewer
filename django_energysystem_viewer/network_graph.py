import igraph as ig
import pandas as pd
import plotly.graph_objects as go
from django.conf import settings
from typing import List, Tuple, Union

def generate_Graph(
        updated_process_set: pd.DataFrame,
        selected_sectors: List[str],
        algorithm: str,
        separate_commodities: str,
        process_specific: str,
        commodity_specific: str,
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
        hoverdistance=-1,
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
            for sector in selected_sectors:
                traces = generate_trace(updated_process_set, sector, algorithm, "sep")
                fig.add_traces(traces)
        elif separate_commodities == "agg":
            for sector in selected_sectors:
                traces = generate_trace(updated_process_set, sector, algorithm, "agg")
                fig.add_traces(traces)
    elif process_specific:
        traces = generate_trace_process_specific(updated_process_set, process_specific)
        fig.add_traces(traces)
    elif commodity_specific:
        traces = generate_trace_commodity_specific(updated_process_set, commodity_specific, selected_sectors)
        fig.add_traces(traces)

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    predefined_order = ["edges_pow","edges_x2x","edges_hea","edges_ind","edges_tra", "pow", "x2x", "hea", "ind", "tra", "pri", "sec", "exo", "iip", "emi"]
    fig = update_layout_with_unique_legend(fig, predefined_order)
    # Update the layout for the legend position
    fig.update_layout(legend=dict(y=0.5, yanchor="middle")
    )

    return fig

def generate_trace(process_set: pd.DataFrame, sector: str, algorithm: str, separate_commodities: str) -> List[
    go.Scatter]:
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
    # process_set = process_set[~process_set["process"].str.endswith(("_ag_0","_ag_1"))]

    inputs, outputs, processes = get_filtered_process_data(process_set, sector)

    nodes, edges = create_nodes_and_edges(inputs, outputs, processes)
    G = ig.Graph(edges)
    layout = generate_layout(G, algorithm)

    labels, node_colors, node_shapes = get_node_attributes(nodes, processes)
    x_offset, y_offset = calculate_offset(sector, algorithm) if separate_commodities == "sep" else (0, 0)

    Xn, Yn = get_node_coordinates(layout, len(nodes), x_offset, y_offset)
    Xe, Ye = get_edge_coordinates(layout, edges, x_offset, y_offset)

    edge_trace = create_edge_trace(Xe, Ye, sector)
    node_traces = create_node_traces_by_color(Xn, Yn, labels, node_shapes, node_colors, processes)

    return [edge_trace] + node_traces

def create_node_trace(Xn: List[float], Yn: List[float], labels: List[str], shapes: List[str], colors: List[str], processes: List[str], sizes: List[int] = None, mode: str = "markers") -> go.Scatter:
    """
    Create a Plotly trace for nodes.

    Parameters:
    Xn (List[float]): X coordinates of nodes.
    Yn (List[float]): Y coordinates of nodes.
    labels (List[str]): Labels for the nodes.
    shapes (List[str]): Shapes of the nodes.
    colors (List[str]): Colors of the nodes.
    sizes (List[int], optional): Sizes of the nodes. Defaults to None.
    mode (str, optional): Mode for the trace. Defaults to "markers".

    Returns:
    go.Scatter: The node trace.
    """
    marker_dict = dict(
        symbol=shapes,
        size=sizes if sizes else 8,
        color=colors,
        line=dict(color="rgb(50,50,50)", width=0.5),
    )

    return go.Scatter(
        x=Xn,
        y=Yn,
        mode=mode,
        name="Nodes",
        marker=marker_dict,
        text=labels,
        hoverinfo="text",
        showlegend=True,
        legendgroup='Nodes'
    )

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


def calculate_offset(sector: str, algorithm: str) -> Tuple[int, int]:
    """
    Calculate the offset for each sector so that the nodes of different sectors do not overlap.

    Parameters:
    sector (str): The sector for which nodes the offset is calculated.
    algorithm (str): The selected algorithm for generating the layout.

    Returns:
    Tuple[int, int]: The x and y offsets for the sector nodes.
    """
    offset_values = {
        "dav": 200,
        "drl": 0,
        "fr": 20,
        "go": 500,
        "kk": 15,
        "lgl": 1500000,
        "mds": 20,
        "umap": 20,
    }
    offset = offset_values.get(algorithm, 0)
    sector_offsets = {
        "x2x": (0, 0),
        "pow": (offset, offset),
        "ind": (offset, -offset),
        "tra": (-offset, offset),
        "hea": (-offset, -offset),
    }
    return sector_offsets.get(sector, (0, 0))

def generate_layout(G: ig.Graph, algorithm: str) -> ig.Layout:
    """
    Generate the layout for the graph according to the selected algorithm.

    Parameters:
    G (ig.Graph): The graph for generating the layout.
    algorithm (str): The selected algorithm for generating the layout.

    Returns:
    ig.Layout: The generated layout.
    """
    layout_mapping = {
        "dav": G.layout_davidson_harel,
        "drl": G.layout_drl,
        "fr": G.layout_fruchterman_reingold,
        "go": G.layout_graphopt,
        "kk": G.layout_kamada_kawai,
        "lgl": G.layout_lgl,
        "mds": G.layout_mds,
        "umap": G.layout_umap,
    }
    layout_func = layout_mapping.get(algorithm)
    return layout_func(dim=2) if layout_func else G.layout_fruchterman_reingold(dim=2)

def get_filtered_process_data(process_set: pd.DataFrame, filter_value: str) -> Tuple[
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
        if sector_abbrv in filter_value:
            filtered_set = pd.concat(
                [filtered_set, process_set[process_set["process"].str.startswith(sector_abbrv)]])
    inputs = filtered_set["input"].tolist()
    outputs = filtered_set["output"].tolist()
    processes = filtered_set["process"].tolist()

    return inputs, outputs, processes


def create_nodes_and_edges(inputs: List[str], outputs: List[str], processes: List[str]) -> Tuple[
    List[str], List[Tuple[int, int]]]:
    """
    Create nodes and edges from inputs, outputs, and processes.

    Parameters:
    inputs (List[str]): List of input nodes.
    outputs (List[str]): List of output nodes.
    processes (List[str]): List of process nodes.

    Returns:
    Tuple[List[str], List[Tuple[int, int]]]: Nodes and edges.
    """
    nodes, edges = [], []

    for i in range(len(processes)):
        input_list = inputs[i].split(",") if isinstance(inputs[i], str) else []
        input_list = [item.strip().replace("[", "").replace("]", "") for item in input_list]

        output_list = outputs[i].split(",") if isinstance(outputs[i], str) else []
        output_list = [item.strip().replace("[", "").replace("]", "") for item in output_list]

        process_list = processes[i].split(",") if isinstance(processes[i], str) else []
        process_list = [item.strip().replace("[", "").replace("]", "") for item in process_list]

        for input_node in input_list:
            if input_node not in nodes:
                nodes.append(input_node)
            source_index = nodes.index(input_node)

            for process_node in process_list:
                if process_node not in nodes:
                    nodes.append(process_node)
                target_index = nodes.index(process_node)
                edges.append((source_index, target_index))

        for process_node in process_list:
            if process_node not in nodes:
                nodes.append(process_node)
            source_index = nodes.index(process_node)

            for output_node in output_list:
                if output_node not in nodes:
                    nodes.append(output_node)
                target_index = nodes.index(output_node)
                edges.append((source_index, target_index))

    return nodes, edges


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


def get_process_node_attributes(nodes: List[str], processes: List[str], process_name: str) -> Tuple[
    List[str], List[str], List[str], List[int]]:
    """
    Get process-specific node attributes including labels, colors, shapes, and sizes.

    Parameters:
    nodes (List[str]): List of nodes.
    processes (List[str]): List of processes.
    process_name (str): The specific process name.

    Returns:
    Tuple[List[str], List[str], List[str], List[int]]: Node labels, colors, shapes, and sizes.
    """
    labels, node_colors, node_shapes, node_sizes = [], [], [], []
    for node in nodes:
        labels.append(node)
        node_colors.append(assign_color(node, processes))
        node_shapes.append(assign_shape(node, processes))
        node_sizes.append(15 if node == process_name else 8)
    return labels, node_colors, node_shapes, node_sizes


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


def get_edge_coordinates(layout: ig.Layout, edges: List[Tuple[int, int]], x_offset: int, y_offset: int) -> Tuple[
    List[float], List[float]]:
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
    Xe, Ye = [], []
    for e in edges:
        Xe += [layout[e[0]][0] + x_offset, layout[e[1]][0] + x_offset, None]
        Ye += [layout[e[0]][1] + y_offset, layout[e[1]][1] + y_offset, None]
    return Xe, Ye


def get_edge_coordinates_from_nodes(Xn: List[float], Yn: List[float], edges: List[Tuple[int, int]]) -> Tuple[
    List[float], List[float]]:
    """
    Get coordinates for edges using node coordinates.

    Parameters:
    Xn (List[float]): X coordinates of nodes.
    Yn (List[float]): Y coordinates of nodes.
    edges (List[Tuple[int, int]]): The list of edges.

    Returns:
    Tuple[List[float], List[float]]: X and Y coordinates of edges.
    """
    Xe, Ye = [], []
    for e in edges:
        Xe += [Xn[e[0]], Xn[e[1]], None]
        Ye += [Yn[e[0]], Yn[e[1]], None]
    return Xe, Ye


def create_edge_trace(Xe: List[float], Ye: List[float], sector: str) -> go.Scatter:
    """
    Create a Plotly trace for edges.

    Parameters:
    Xe (List[float]): X coordinates of edges.
    Ye (List[float]): Y coordinates of edges.
    sector (str): The sector to which the edges belong.

    Returns:
    go.Scatter: The edge trace.
    """
    return go.Scatter(
        x=Xe,
        y=Ye,
        mode="lines",
        line=dict(color="rgb(125,125,125)", width=1),
        hoverinfo="none",
        showlegend=True,
        name=f'edges_{sector}'
    )


def create_node_traces_by_color(Xn: List[float], Yn: List[float], labels: List[str], shapes: List[str],
                                colors: List[str], processes: List[str], sizes: List[int] = None,
                                mode: str = "markers") -> List[go.Scatter]:
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
        trace_sizes = [sizes[i] if sizes else 8 for i in indices]

        legend_name = trace_labels[0][:3]
        legend_entry = (legend_name, color)

        if legend_entry not in legend_added:
            show_legend = True
            legend_added.add(legend_entry)
        else:
            show_legend = False

        node_trace = go.Scatter(
            x=trace_Xn,
            y=trace_Yn,
            mode=mode,
            name=legend_name,
            marker=dict(
                symbol=trace_shapes,
                size=trace_sizes,
                color=color,
                line=dict(color="rgb(50,50,50)", width=0.5),
            ),
            text=trace_labels,
            hoverinfo="text",
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
            legend_entry = (trace.name, trace.marker.color)
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
                legend_entry = (trace.name, trace.marker.color)
                if legend_entry not in legend_added:
                    trace.showlegend = True
                    legend_added.add(legend_entry)
                else:
                    trace.showlegend = False
                ordered_traces.append(trace)

    # Clear existing traces and add ordered traces
    fig.data = []
    for trace in ordered_traces:
        fig.add_trace(trace)

    return fig



def get_process_node_coordinates(num_inputs: int, num_outputs: int) -> Tuple[List[float], List[float]]:
    """
    Get coordinates for process-specific nodes.

    Parameters:
    num_inputs (int): The number of input nodes.
    num_outputs (int): The number of output nodes.

    Returns:
    Tuple[List[float], List[float]]: X and Y coordinates of process-specific nodes.
    """
    Xn, Yn = [], []

    for i in range(num_inputs):
        Xn.append(-1)
        Yn.append(i + 0.5 - num_inputs / 2)
    Xn.append(0)
    Yn.append(0)
    for i in range(num_outputs):
        Xn.append(1)
        Yn.append(i + 0.5 - num_outputs / 2)
    return Xn, Yn


def get_commodity_node_coordinates(num_inputs: int, num_outputs: int) -> Tuple[List[float], List[float]]:
    """
    Get coordinates for commodity-specific nodes.

    Parameters:
    num_inputs (int): The number of input nodes.
    num_outputs (int): The number of output nodes.

    Returns:
    Tuple[List[float], List[float]]: X and Y coordinates of commodity-specific nodes.
    """
    Xn, Yn = [0], [0]
    j, k = 0, 0

    for i in range(num_inputs):
        Xn.append(-1)
        Yn.append(j + 0.5 - num_inputs / 2)
        j += 1

    for i in range(num_outputs):
        Xn.append(1)
        Yn.append(k + 0.5 - num_outputs / 2)
        k += 1

    return Xn, Yn

def generate_trace_process_specific(updated_process_set, process_name):
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
    # Filter the process set for the selected process
    filtered_process_set = updated_process_set[updated_process_set["process"].str.startswith(process_name)]

    # Initialize the lists for the inputs, outputs, and processes
    inputs = filtered_process_set["input"].tolist()
    outputs = filtered_process_set["output"].tolist()
    processes = filtered_process_set["process"].tolist()

    nodes = []
    edges = []

    # Create all nodes and then all edges of the format (source_index, target_index)
    for i, process in enumerate(processes):
        input_value = inputs[i]
        output_value = outputs[i]
        process_value = processes[i]

        # Parse input, output, and process values correctly
        input_list = input_value.split(",") if isinstance(input_value, str) else input_value
        input_list = [item.strip().replace("[", "").replace("]", "") for item in input_list]

        output_list = output_value.split(",") if isinstance(output_value, str) else output_value
        output_list = [item.strip().replace("[", "").replace("]", "") for item in output_list]

        process_list = process_value.split(",") if isinstance(process_value, str) else process_value
        process_list = [item.strip().replace("[", "").replace("]", "") for item in process_list]

        nodes.append(process_name)

        for input_node in input_list:
            input_node = input_node.strip()
            if input_node not in nodes:
                nodes.append(input_node)
            source_index = nodes.index(input_node)

            for process_node in process_list:
                process_node = process_node.strip()
                if process_node not in nodes:
                    nodes.append(process_node)
                target_index = nodes.index(process_node)
                edges.append((source_index, target_index))

        for process_node in process_list:
            process_node = process_node.strip()
            if process_node not in nodes:
                nodes.append(process_node)
            source_index = nodes.index(process_node)

            for output_node in output_list:
                output_node = output_node.strip()
                if output_node not in nodes:
                    nodes.append(output_node)
                target_index = nodes.index(output_node)
                edges.append((source_index, target_index))

    # Initialize the lists for the labels, colors, and shapes of the nodes
    node_colors = [assign_color(node, process_list) for node in nodes]
    node_shapes = [assign_shape(node, process_list) for node in nodes]
    node_sizes = [15 if node in process_list else 8 for node in nodes]

    # The process node should be displayed in the center, the inputs on the left, and the outputs on the right
    Xn = [0]  # Center node x-coordinate
    Yn = [0]  # Center node y-coordinate

    # Add coordinates for the input nodes
    for i in range(len(input_list)):
        Xn.append(-1)
        Yn.append(i + 0.5 - len(input_list) / 2)

    # Add coordinates for the output nodes
    for i in range(len(output_list)):
        Xn.append(1)
        Yn.append(i + 0.5 - len(output_list) / 2)

    # Assign the calculated coordinates to the edges
    Xe, Ye = [], []
    for e in edges:
        Xe += [Xn[e[0]], Xn[e[1]], None]
        Ye += [Yn[e[0]], Yn[e[1]], None]

    # Create the edge trace
    edge_trace = go.Scatter(
        x=Xe,
        y=Ye,
        mode="lines",
        line=dict(color="rgb(125,125,125)", width=1),
        hoverinfo="none",
    )

    # Create the node trace
    node_trace = go.Scatter(
        x=Xn,
        y=Yn,
        mode="markers+text",
        name="actors",
        marker=dict(
            symbol=node_shapes,
            size=node_sizes,
            color=node_colors,
            line=dict(color="rgb(50,50,50)", width=0.5),
        ),
        text=nodes,
        textposition="bottom center",
        hoverinfo="text",
    )

    return [edge_trace, node_trace]

def generate_trace_commodity_specific(updated_process_set, commodity_name, selected_sectors):
    """
    Generates the trace for the selected commodity. All processes that produce the selected commodity are displayed to
    the left of the commodity, all processes that consume the selected commodity are displayed to the right of the
    commodity.

    Parameters
    ----------
    commodity_name: str
        The selected commodity, which is used to filter the process set.
    selected_sectors: list
        The selected sectors, which are used to filter the process set.
    file: str
        The path to the Excel file of the Model Structure.

    Returns
    -------
    list
        The combined trace of nodes and edges, including their colours and shapes."""

    # filter process set for the selected sectors
    updated_process_set = updated_process_set[updated_process_set["process"].str.startswith(tuple(selected_sectors))]

    # filter the process set to only include processes that produce or consume the selected commodity
    filtered_process_set = updated_process_set[
        (updated_process_set["input"].str.contains(commodity_name))
        | (updated_process_set["output"].str.contains(commodity_name))
    ]

    # get the inputs, outputs and processes of the filtered process set
    inputs = filtered_process_set["input"].tolist()
    outputs = filtered_process_set["output"].tolist()
    processes = filtered_process_set["process"].tolist()

    nodes = []
    edges = []

    # add the selected commodity to the nodes list
    nodes.append(commodity_name)

    process_input = []
    process_output = []

    # create all nodes and then all edges of the format (source_index, target_index)
    for i, process in enumerate(processes):
        input_value = inputs[i]
        output_value = outputs[i]
        process_value = processes[i]

        # if the commodity is an input of the process, the process is added to the nodes list and the edge is added to
        # the edges list if the commodity is an output of the process, the process is added to the nodes list and the
        # edge is added to the edges list
        if commodity_name in input_value:
            nodes.append(process_value)
            edges.append((nodes.index(commodity_name), nodes.index(process_value)))
            process_input.append(process_value)
        elif commodity_name in output_value:
            nodes.append(process_value)
            edges.append((nodes.index(process_value), nodes.index(commodity_name)))
            process_output.append(process_value)

    # initialize the lists for the colors and shapes of the nodes
    node_color = []
    node_shape = []

    for node in nodes:
        node_color.append(assign_color(node, processes))
        node_shape.append(assign_shape(node, processes))

    # the commodity node should be displayed in the center, the processes where it is an output on the left and the
    # processes where it is an input on the right the appropriate coordinates have to be assigned to each node

    Xn = []
    Yn = []

    # add coordinates of the commodity node
    Xn += [0]
    Yn += [0]

    # we need two counters, one for the inputs and one for the outputs, to calculate the y-coordinates of the
    # processes, as i iterates over the node list
    j = 0
    k = 0

    for i in range(len(nodes)):
        if nodes[i] in process_input:
            Xn += [len(process_input) + len(process_output)]
            Yn += [j + 0.5 - len(process_input) / 2]
            j += 1
        elif nodes[i] in process_output:
            Xn += [-len(process_output) - len(process_input)]
            Yn += [k + 0.5 - len(process_output) / 2]
            k += 1

    # assign the calculated coordinates to the edges
    Xe = []
    Ye = []

    for e in edges:
        Xe += [Xn[e[0]], Xn[e[1]], None]
        Ye += [Yn[e[0]], Yn[e[1]], None]

    edge_trace = go.Scatter(
        x=Xe,
        y=Ye,
        mode="lines",
        line=dict(color="rgb(125,125,125)", width=1),
        hoverinfo="none",
    )

    node_trace = go.Scatter(
        x=Xn,
        y=Yn,
        mode="markers",
        name="actors",
        marker=dict(
            symbol=node_shape,
            size=8,
            color=node_color,
            line=dict(color="rgb(50,50,50)", width=0.5),
        ),
        text=nodes,
        hoverinfo="text",
    )

    data = [edge_trace, node_trace]

    return data