import igraph as ig
import pandas as pd
import plotly.graph_objects as go
from django.conf import settings


# generate the trace for the selected sector and algorithm
def generate_trace(sector, algorithm):
    """Generates the trace for the selected sector and algorithm.

    Parameters
    ----------
    sector: str
        The selected sector, which is used to filter the process set.
    algorithm: str
        The selected algorithm, which is used to generate the layout.

    Returns
    -------
    list
        The combined trace of nodes and edges, including their colours and shapes.
    """

    # load the process set, change the path if necessary
    updated_process_set = pd.read_excel(settings.MODEL_STRUCTURE_FILE, "Process_Set")

    filtered_process_set = updated_process_set[updated_process_set["process"].str.startswith(sector)]

    inputs = filtered_process_set["input"].tolist()
    outputs = filtered_process_set["output"].tolist()
    processes = filtered_process_set["process"].tolist()

    nodes = []
    edges = []

    process_list = []

    # create all nodes and then all edges of the format (source_index, target_index)
    for i, process in enumerate(processes):
        input_value = inputs[i]
        output_value = outputs[i]
        process_value = processes[i]

        if isinstance(input_value, str):
            input_list = input_value.split(",")
        else:
            input_list = []

        if isinstance(output_value, str):
            output_list = output_value.split(",")
        else:
            output_list = []

        if isinstance(process_value, str):
            process_list = process_value.split(",")
        else:
            process_list = []

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

    G = ig.Graph(edges)

    # create layout with the selected algorithm
    layt = generate_layout(G, algorithm)

    labels = []
    node_color = []
    node_shape = []

    def assign_color(node):
        """Assigns a color to each node, depending on their sector.

        For processes, the colors chosen are red for power, green for x2x, blue for industry, yellow for mobility,
        magenta for heat. For inputs and outputs, the colors chosen are dark red for primary, red for secondary,
        orange for exogenous, light orange for intermediate.

        Parameters
        ----------
        node: str
            The node to assign a color to.

        Returns
        -------
        str
            The assigned color of the node.
        """

        if node in processes:
            sector_colors = {
                "pow": "rgb(255, 0, 0)",  # Red
                "x2x": "rgb(0, 255, 0)",  # Green
                "ind": "rgb(0, 0, 255)",  # Blue
                "mob": "rgb(255, 255, 0)",  # Yellow
                "hea": "rgb(255, 0, 255)",  # Magenta
            }

            sector = node[:3]  # Extract the first three letters of the node name

            if sector in sector_colors:
                color = sector_colors[sector]
            else:
                color = "rgb(128, 128, 128)"  # Default color for other sectors

            return color

        if node not in processes:
            source_colors = {
                "pri": "#4F000B",  # Dark red
                "sec": "#720026",  # Red
                "exo": "#FF7F51",  # Orange
                "iip": "#FF9B54",  # Light orange
            }

            source = node[:3]  # Extract the first three letters of the node name

            if source in source_colors:
                color = source_colors[source]
            else:
                color = "rgb(128, 128, 128)"

            return color

    def assign_shape(node):
        """Assigns a shape to each node, depending on whether it is a process or an input/output.

        Parameters
        ----------
        node: str
            The node to assign a shape to.

        Returns
        -------
        str
            The assigned shape of the node.
        """

        if node in processes:
            shape = "square"
        else:
            shape = "circle"

        return shape

    # assign color and shape to each node
    for node in nodes:
        labels.append(node)
        node_color.append(assign_color(node))
        node_shape.append(assign_shape(node))

    # assign offset to each node depending on the sector
    def calculate_offset(sector):
        """Calculates the offset for each sector, so that the nodes of the different sectors are not overlapping.

        Parameters
        ----------
        sector: str
            The sector, for which nodes the offset is calculated.

        Returns
        -------
        int
            The x offset of the nodes of the sector.
        int
            The y offset of the nodes of the sector.
        """

        sector_offsets = {
            "x2x": [0, 0],
            "pow": [15, 15],
            "ind": [15, -15],
            "mob": [-15, 15],
            "hea": [-15, -15],
        }

        if sector in sector_offsets:
            x_offset = sector_offsets[sector][0]
            y_offset = sector_offsets[sector][1]
        else:
            x_offset = 0
            y_offset = 0

        return x_offset, y_offset

    x_offset, y_offset = calculate_offset(sector)

    N = len(nodes)
    # assign calculated positions to each node
    Xn = []
    Yn = []
    # add Zn = [] for 3d plot

    for k in range(N):
        Xn += [layt[k][0] + x_offset]
        Yn += [layt[k][1] + y_offset]
        # Zn += [layt[k][2]] for 3d plot

    # assign the calculated coordinates to the edges
    Xe = []
    Ye = []
    # Ze = [] for 3d plot

    for e in edges:
        Xe += [layt[e[0]][0] + x_offset, layt[e[1]][0] + x_offset, None]
        Ye += [layt[e[0]][1] + y_offset, layt[e[1]][1] + y_offset, None]
        # Ze += [layt[e[0]][2], layt[e[1]][2], None] for 3d plot

    edge_trace = go.Scatter(
        x=Xe,
        y=Ye,
        # z=Ze,
        mode="lines",
        line=dict(color="rgb(125,125,125)", width=1),
        hoverinfo="none",
    )

    node_trace = go.Scatter(
        x=Xn,
        y=Yn,
        # z=Zn,
        mode="markers",
        name="actors",
        marker=dict(
            symbol=node_shape,
            size=6,
            color=node_color,
            line=dict(color="rgb(50,50,50)", width=0.5),
        ),
        text=labels,
        hoverinfo="text",
    )

    data = [edge_trace, node_trace]

    return data


# generate the graph
def generate_Graph(selected_sectors, algorithm):
    """Generates the graph for the selected sectors and algorithm.

    Parameters
    ----------
    selected_sectors: list
        The selected sectors, which are used to filter the process set.
    algorithm: str
        The selected algorithm, which is used to generate the layout.

    Returns
    -------
    plotly.graph_objects.Figure
        The generated graph.
    """
    axis = dict(
        showbackground=False,
        showline=False,
        zeroline=False,
        showgrid=False,
        showticklabels=False,
        title="",
        showspikes=False,
        visible=False,
    )

    graph_layout = go.Layout(
        width=960,
        height=800,
        plot_bgcolor="white",
        showlegend=True,
        hovermode="closest",
        hoverdistance=-1,
        spikedistance=-1,
        scene=dict(
            xaxis=dict(axis),
            yaxis=dict(axis),
            # zaxis=dict(axis),
        ),
        margin=dict(autoexpand=True),
    )

    fig = go.Figure(layout=graph_layout)

    # add traces for each selected sector
    for sector in selected_sectors:
        traces = generate_trace(sector, algorithm)
        fig.add_trace(traces[0])
        fig.add_trace(traces[1])

    # remove axis scales
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)

    # add legend
    legend = dict(
        yanchor="top",
        y=0.99,
        xanchor="right",
        x=1.2,
    )

    fig.update_layout(legend=legend)

    return fig


def generate_layout(G, algorithm):
    """Generates the layout for the graph according to the selected algorithm.

    Parameters
    ----------
    G: igraph.Graph
        The graph, which is used to generate the layout.
    algorithm: str
        The selected algorithm.

    Returns
    -------
    list
        The generated layout.
    """
    if algorithm == "dav":
        layout = G.layout_davidson_harel()
    elif algorithm == "drl":
        layout = G.layout_drl(dim=2)
    elif algorithm == "fr":
        layout = G.layout_fruchterman_reingold(dim=2)
    elif algorithm == "go":
        layout = G.layout_graphopt()
    elif algorithm == "kk":
        layout = G.layout_kamada_kawai(dim=2)
    elif algorithm == "lgl":
        layout = G.layout_lgl()
    elif algorithm == "mds":
        layout = G.layout_mds()
    elif algorithm == "umap":
        layout = G.layout_umap()

    return layout
