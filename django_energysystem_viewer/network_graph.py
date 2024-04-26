import igraph as ig
import pandas as pd
import plotly.graph_objects as go
from django.conf import settings


# generate the trace for the selected sector and algorithm
def generate_trace(updated_process_set, sector, algorithm, seperate_commodities):
    """Generates the trace for the selected sector and algorithm.

    Parameters
    ----------
    sector: str
        The selected sector, which is used to filter the process set or in the case of aggregated commodities, a string
        of the selected sectors.
    algorithm: str
        The selected algorithm, which is used to generate the layout.
    seperate_commodities: str
        The selected option, whether the commodities should be seperated or aggregated.
    file: str
        The path to the Excel file of the Model Structure.

    Returns
    -------
    list
        The combined trace of nodes and edges, including their colours and shapes.
    """

    # filter aggregations as first step
    # updated_process_set = updated_process_set[~updated_process_set["process"].str.endswith("_ag")]

    # initialize the lists for the inputs, outputs and processes
    inputs = []
    outputs = []
    processes = []

    # in the case that the commodities are seperate, the nodes and edges are created for each sector seperately
    if seperate_commodities == "sep":
        filtered_process_set = updated_process_set[updated_process_set["process"].str.startswith(sector)]

        inputs = filtered_process_set["input"].tolist()
        outputs = filtered_process_set["output"].tolist()
        processes = filtered_process_set["process"].tolist()
    # in the case that the commodities are aggregated, the nodes and edges of the selected sectors are created together
    elif seperate_commodities == "agg":
        sector_abbrvs = ["pow", "x2x", "ind", "tra", "hea", "hel"]
        for sector_abbrv in sector_abbrvs:
            if sector_abbrv in sector:
                filtered_process_set = updated_process_set[updated_process_set["process"].str.startswith(sector_abbrv)]

                inputs += filtered_process_set["input"].tolist()
                outputs += filtered_process_set["output"].tolist()
                processes += filtered_process_set["process"].tolist()

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

        # remove brackets from input_list -> brackets cause problems with color assignment
        input_list = [item.replace("[", "").replace("]", "") for item in input_list]

        if isinstance(output_value, str):
            output_list = output_value.split(",")
        else:
            output_list = []

        # remove brackets from output_list -> brackets cause problems with color assignment
        output_list = [item.replace("[", "").replace("]", "") for item in output_list]

        if isinstance(process_value, str):
            process_list = process_value.split(",")
        else:
            process_list = []

        # remove brackets from process_list -> brackets cause problems with color assignment
        process_list = [item.replace("[", "").replace("]", "") for item in process_list]

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

    # assign color and shape to each node
    for node in nodes:
        labels.append(node)
        node_color.append(assign_color(node, processes))
        node_shape.append(assign_shape(node, processes))

    # calculate the offset for each sector if the commodities are seperated
    if seperate_commodities == "sep":
        x_offset, y_offset = calculate_offset(sector, algorithm)
    elif seperate_commodities == "agg":
        x_offset, y_offset = 0, 0

    N = len(nodes)
    # assign calculated positions to each node
    Xn = []
    Yn = []

    for k in range(N):
        Xn += [layt[k][0] + x_offset]
        Yn += [layt[k][1] + y_offset]

    # assign the calculated coordinates to the edges
    Xe = []
    Ye = []

    for e in edges:
        Xe += [layt[e[0]][0] + x_offset, layt[e[1]][0] + x_offset, None]
        Ye += [layt[e[0]][1] + y_offset, layt[e[1]][1] + y_offset, None]

    edge_trace = go.Scatter(
        x=Xe,
        y=Ye,
        mode="lines+markers",
        line=dict(color="rgb(125,125,125)", width=1),
        hoverinfo="none",
    )

    # # Create arrowhead traces
    # arrowhead_traces = []
    # for i in range(len(Xe)):
    #     arrowhead_trace = go.Scatter(
    #         x=[Xe[i]],
    #         y=[Ye[i]],
    #         mode="markers",
    #         marker=dict(size=10, symbol="arrow-up-open"),
    #         hoverinfo="none",
    #     )
    #     arrowhead_traces.append(arrowhead_trace)

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
        text=labels,
        hoverinfo="text",
    )

    data = [edge_trace, node_trace]

    return data


def generate_trace_process_specific(process_name):
    """Generates the trace for the selected process.

    Parameters
    ----------
    process_name: str
        The selected process, which is used to filter the process set.
    file: str
        The path to the Excel file of the Model Structure.

    Returns
    -------
    list
        The combined trace of nodes and edges, including their colours and shapes."""

    # load the process set, change the path if necessary
    updated_process_set = pd.read_excel(settings.MEDIA_ROOT + "/" + settings.MODEL_STRUCTURE_FILE, "Process_Set")

    # initialize the lists for the inputs, outputs and processes
    inputs = []
    outputs = []
    processes = []

    # filter the process set for the selected process such that only the selected process and its inputs and outputs
    # are included
    filtered_process_set = updated_process_set[updated_process_set["process"].str.startswith(process_name)]

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

        # remove brackets from input_list -> brackets cause problems with color assignment
        input_list = [item.replace("[", "").replace("]", "") for item in input_list]

        if isinstance(output_value, str):
            output_list = output_value.split(",")
        else:
            output_list = []

        # remove brackets from output_list -> brackets cause problems with color assignment
        output_list = [item.replace("[", "").replace("]", "") for item in output_list]

        if isinstance(process_value, str):
            process_list = process_value.split(",")
        else:
            process_list = []

        # remove brackets from process_list -> brackets cause problems with color assignment
        process_list = [item.replace("[", "").replace("]", "") for item in process_list]

        nodes.append(process_name)

        # right now, only single process names can be searched for, not multiple, so the for loop is not necessary but
        # kept for future use
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

        # initialize the lists for the labels, colors and shapes of the nodes
        node_color = []
        node_shape = []
        node_size = []

        for node in nodes:
            node_color.append(assign_color(node, process_list))
            node_shape.append(assign_shape(node, process_list))
            if node in process_list:
                node_size.append(15)
            else:
                node_size.append(8)

        # the process node should be displayed in the center, the inputs on the left, and the outputs on the right
        # the appropriate coordinates have to be assigned to each node
        # the y-coordinates of the inputs and outputs should be that they are evenly distributed around 0, which is the
        # y-coordinate of the process node

        Xn = []
        Yn = []

        # add coordinates of the process node
        Xn += [0]
        Yn += [0]

        # add coordinates of the inputs
        for i in range(len(input_list)):
            Xn += [-1]
            Yn += [i + 0.5 - len(input_list) / 2]

        # add coordinates of the outputs
        for i in range(len(output_list)):
            Xn += [1]
            Yn += [i + 0.5 - len(output_list) / 2]

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
            mode="markers+text",
            name="actors",
            marker=dict(
                symbol=node_shape,
                size=node_size,
                color=node_color,
                line=dict(color="rgb(50,50,50)", width=0.5),
            ),
            text=nodes,
            textposition="bottom center",
            hoverinfo="text",
        )

        data = [edge_trace, node_trace]

        return data


def generate_trace_commodity_specific(commodity_name, selected_sectors):
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

    # load the process set, change the path if necessary
    process_set = pd.read_excel(settings.MEDIA_ROOT + "/" + settings.MODEL_STRUCTURE_FILE, "Process_Set")

    # initialize the lists for the inputs, outputs and processes
    inputs = []
    outputs = []
    processes = []

    # filter process set for the selected sectors
    updated_process_set = process_set[process_set["process"].str.startswith(tuple(selected_sectors))]

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


def assign_color(node, processes):
    """Assigns a color to each node, depending on their sector.

    For processes, the colors chosen are red for power, green for x2x, blue for industry, yellow for transport, magenta
    for heat. For inputs and outputs, the colors chosen are dark red for primary, red for secondary, orange for
    exogenous, light orange for intermediate.

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
            "pow": "rgb(255, 255, 0)",  # Yellow
            "x2x": "rgb(0, 0, 255)",  # Blue
            "ind": "rgb(255, 0, 255)",  # Magenta
            "tra": "#17cda6",  # Turquoise
            "hea": "rgb(255, 0, 0)",  # Red
            "hel": "rgb(0, 0, 0)",  # black
        }

        sector = node[:3]  # Extract the first three letters of the node name

        if sector in sector_colors:
            color = sector_colors[sector]
        else:
            color = "rgb(128, 128, 128)"  # Default color for other sectors

        return color

    if node not in processes:
        source_colors = {
            "pri": "#FFFFFF",  # white
            "sec": "#6aa84f",  # Green
            "exo": "#ED7D31",  # Orange
            "iip": "#9999CC",  # Violett
        }

        source = node[:3]  # Extract the first three letters of the node name

        if source in source_colors:
            color = source_colors[source]
        else:
            color = "rgb(128, 128, 128)"

        return color


def assign_shape(node, processes):
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


def calculate_offset(sector, algorithm):
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

    if algorithm == "dav":
        offset = 200
    elif algorithm == "drl":
        offset = 0
    elif algorithm == "fr":
        offset = 20
    elif algorithm == "go":
        offset = 500
    elif algorithm == "kk":
        offset = 15
    elif algorithm == "lgl":
        offset = 1500000
    elif algorithm == "mds":
        offset = 20
    elif algorithm == "umap":
        offset = 20
    else:
        offset = 0

    sector_offsets = {
        "x2x": [0, 0],
        "pow": [offset, offset],
        "ind": [offset, -offset],
        "tra": [-offset, offset],
        "hea": [-offset, -offset],
    }

    if sector in sector_offsets:
        x_offset = sector_offsets[sector][0]
        y_offset = sector_offsets[sector][1]
    else:
        x_offset = 0
        y_offset = 0

    return x_offset, y_offset


# generate the graph
def generate_Graph(
    updated_process_set,
    selected_sectors,
    algorithm,
    seperate_commodities,
    process_specific,
    commodity_specific,
):
    """Generates the graph for the selected sectors and algorithm.

    Parameters
    ----------
    selected_sectors: list
        The selected sectors, which are used to filter the process set.
    algorithm: str
        The selected algorithm, which is used to generate the layout.
    seperate_commodities: str
        The selected option, whether the commodities should be seperated or aggregated.
    process_specific: str
        The selected process, which is used to generate the graph, in the case a specific process is searched for.
    commodity_specific: str
        The selected comodity, which is used to generate the graph, in the case a specific comodity is searched for.
    file: str
        The path to the Excel file of the Model Structure.

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
        autosize=True,
        height=650,
        showlegend=False,
        hovermode="closest",
        hoverdistance=-1,
        spikedistance=-1,
        scene=dict(
            xaxis=dict(axis),
            yaxis=dict(axis),
        ),
        margin=dict(l=0, r=0, t=0, b=0, autoexpand=False),
    )

    fig = go.Figure(layout=graph_layout)

    if not process_specific and not commodity_specific:
        # add traces for each selected sector and depending on whether the commodities are seperated or aggregated
        if seperate_commodities == "sep":
            for sector in selected_sectors:
                traces = generate_trace(updated_process_set, sector, algorithm, "sep")
                fig.add_trace(traces[0])
                fig.add_trace(traces[1])
        elif seperate_commodities == "agg":
            # if commodities are aggregated, the selected sectors are combined to one string to use them in the
            # generate_trace function
            traces = generate_trace(updated_process_set, "".join(selected_sectors), algorithm, "agg")
            fig.add_trace(traces[0])
            fig.add_trace(traces[1])

    elif process_specific:
        traces = generate_trace_process_specific(process_specific)
        fig.add_trace(traces[0])
        fig.add_trace(traces[1])

    elif commodity_specific:
        traces = generate_trace_commodity_specific(commodity_specific, selected_sectors)
        fig.add_trace(traces[0])
        fig.add_trace(traces[1])

    # remove axis scales
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)

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
