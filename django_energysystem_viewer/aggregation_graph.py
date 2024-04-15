# from dash import html, State, Input, Output
# import dash_bootstrap_components as dbc
# import dash_cytoscape as cyto
from openpyxl import load_workbook


def generate_aggregation_graph(file):
    """Generates the aggregation graph as a dash component using the functions below.

    Parameters
    ----------
    file: str
        The path to the Excel file of the Model Structure.

    Returns
    -------
    html.Div
        The aggregation graph component."""
    # collapsed nodes
    collapsed_nodes = []

    # aggregation level initial value
    level_of_detail = 1

    sector = "pow"

    # create nodes and edges
    nodes, edges = generate_elements(file, level_of_detail, sector)

    # elements that are to be displayed after collapsing
    elements = elements_after_collapse(collapsed_nodes, nodes, edges)

    # create tree graph
    tree_graph = create_tree(elements)

    collapse_expand_callback(app, collapsed_nodes, file)

    detail_level_callback(app, file, collapsed_nodes)

    return tree_graph


def get_background_color(cell_address, sheet):
    """Finds the background color of a cell. Used to filter the aggregation levels.

    Parameters
    ----------
    cell_address: str
        The address of the cell.
    sheet: str
        The sheet of the Excel file of the Model Structure.

    Returns
    -------
    str
        The background color of the cell.
    """
    cell = sheet[cell_address]
    return cell.fill.start_color.index


def get_aggregation_level(color, sheet):
    """Returns a list of all processes of one aggregation level according to the background color of the corresponding cell.

    Parameters
    ----------
    color: str
        The background color of the cell.
    sheet: str
        The sheet of the Excel file of the Model Structure.

    Returns
    -------
    list
        The list of elements of the corresponding aggregation level.
    """
    elements = []

    for row in sheet.iter_rows(min_row=2, min_col=1, max_col=2):
        for cell in row:
            if cell.fill.start_color.index == color:
                elements.append(cell.value)

    # remove duplicates
    elements = list(dict.fromkeys(elements))

    return elements


def generate_elements(file, level_of_detail, sector):
    """Generates the nodes and edges of the aggregation graph.

    Parameters
    ----------
    file: str
        The path to the Excel file of the Model Structure.
    level_of_detail: int
        The desired level of detail.

    Returns
    -------
    list
        The list of all nodes.
    list
        The list of all edges.
    """

    # load workbook and sheet
    wb = load_workbook(file)
    sheet = wb["Aggregation_Mapping"]

    process_list = []
    detailled_data = []
    aggregation_level_1 = []
    aggregation_level_2 = []
    aggregation_level_3 = []

    # create lists of the aggregation levels and list of all processes
    cell_address_aggregation_level_3 = "D5"
    aggregation_level_3 = get_aggregation_level(
        get_background_color(cell_address_aggregation_level_3, sheet), sheet
    )
    filtered_aggregation_level_3 = [
        item for item in aggregation_level_3 if item.startswith(sector)
    ]
    cell_address_aggregation_level_2 = "D4"
    aggregation_level_2 = get_aggregation_level(
        get_background_color(cell_address_aggregation_level_2, sheet), sheet
    )
    filtered_aggregation_level_2 = [
        item for item in aggregation_level_2 if item.startswith(sector)
    ]
    cell_address_aggregation_level_1 = "D3"
    aggregation_level_1 = get_aggregation_level(
        get_background_color(cell_address_aggregation_level_1, sheet), sheet
    )
    filtered_aggregation_level_1 = [
        item for item in aggregation_level_1 if item.startswith(sector)
    ]
    cell_address_detailled_data = "D2"
    detailled_data = get_aggregation_level(
        get_background_color(cell_address_detailled_data, sheet), sheet
    )
    filtered_detailled_data = [
        item for item in detailled_data if item.startswith(sector)
    ]

    process_list = (
        filtered_aggregation_level_3
        + filtered_aggregation_level_2
        + filtered_aggregation_level_1
        + filtered_detailled_data
    )

    # create nodes
    nodes = []

    def calc_pos(node):
        """Assigns the position of a node according to its aggregation level.

        Parameters
        ----------
        node: str
            The node, that a position should be assigned to.

        Returns
        -------
        int
            The x-coordinate of the node.
        int
            The y-coordinate of the node.
        """
        # scaling factors for the x and y coordinates
        if level_of_detail == 1:
            scaling_factor_x = 2000
        else:
            scaling_factor_x = 2000
        scaling_factor_y = 150

        if node in filtered_detailled_data:
            N = len(filtered_detailled_data)
            span = N * scaling_factor_y
            y = filtered_detailled_data.index(node) * scaling_factor_y - span / 2
            x = 4 * scaling_factor_x
        elif node in filtered_aggregation_level_1:
            N = len(filtered_aggregation_level_1)
            span = N * scaling_factor_y
            y = filtered_aggregation_level_1.index(node) * scaling_factor_y - span / 2
            x = 3 * scaling_factor_x
        elif node in filtered_aggregation_level_2:
            N = len(filtered_aggregation_level_2)
            span = N * scaling_factor_y
            y = filtered_aggregation_level_2.index(node) * scaling_factor_y - span / 2
            x = 2 * scaling_factor_x
        elif node in filtered_aggregation_level_3:
            N = len(filtered_aggregation_level_3)
            span = N * scaling_factor_y
            y = filtered_aggregation_level_3.index(node) * scaling_factor_y - span / 2
            x = 1 * scaling_factor_x
        else:
            y = 0
            x = 0
        return x, y

    for node in process_list:
        x, y = calc_pos(node)
        nodes.append(
            {
                "data": {"id": node, "label": node},
                "position": {"x": x, "y": y},
                "classes": "",
                "collapsible": False,
                "level_of_detail": -1,
            }
        )

    # add aggregation level of node to classes property
    for node in nodes:
        if node["data"]["id"] in aggregation_level_1:
            node["classes"] = "aggregation_level_1"
        elif node["data"]["id"] in aggregation_level_2:
            node["classes"] = "aggregation_level_2"
        elif node["data"]["id"] in aggregation_level_3:
            node["classes"] = "aggregation_level_3"

    # create edges
    edges = []

    # iterate over all rows and columns: if the cell and the cell to the right are both in the list of processes, add an edge
    # if the cell is empty and the cell to the right is not, go up until a cell with a process is found and add an edge between the two
    for row in sheet.iter_rows(min_row=2, min_col=1, max_col=1):
        for cell in row:
            if (
                cell.value in process_list
                and cell.offset(column=1).value in process_list
            ):
                edges.append(
                    {
                        "data": {
                            "source": cell.value,
                            "target": cell.offset(column=1).value,
                        }
                    }
                )
                # if this is the case, the source cell is a parent node and is collapsible. This is used in the stylesheet to style the nodes differently.
                for node in nodes:
                    if node["data"]["id"] == cell.value:
                        node["collapsible"] = True
                        break
            elif cell.value is None and cell.offset(column=1).value is not None:
                i = 1
                while cell.offset(row=-i).value is None:
                    i += 1
                if (
                    cell.offset(row=-i).value in process_list
                    and cell.offset(column=1).value in process_list
                ):
                    edges.append(
                        {
                            "data": {
                                "source": cell.offset(row=-i).value,
                                "target": cell.offset(column=1).value,
                            }
                        }
                    )
            elif cell.value not in process_list:
                continue

    # add sector root nodes
    nodes.append(
        {
            "data": {"id": sector, "label": sector},
            "position": {"x": 0, "y": 0},
            "classes": "not-collapsed",
            "collapsible": True,
            "level_of_detail": 0,
        }
    )

    # add edge from root node to all nodes that do not have a parent and therefore will not be aggregated further
    # therefore the level of detail is set to 1
    for node in process_list:
        for edge in edges:
            if edge["data"]["target"] == node:
                break
        else:
            sec = node[:3]
            edges.append({"data": {"source": sec, "target": node}})

    # if source node has level of detail equal to 1, the target node is assigned level of detail 2 and so on
    # the changed variable is used to check if the level of detail of any node has changed in the current iteration
    changed = True
    while changed:
        changed = False
        for edge in edges:
            for source_node in nodes:
                # if the source node has level of detail -1, it has not been assigned a level of detail yet, but will be in a future iteration
                if edge["data"]["source"] == source_node["data"]["id"]:
                    for target_node in nodes:
                        if (
                            edge["data"]["target"] == target_node["data"]["id"]
                            and source_node["level_of_detail"] != -1
                        ):
                            if (
                                target_node["level_of_detail"]
                                != source_node["level_of_detail"] + 1
                            ):
                                target_node["level_of_detail"] = (
                                    source_node["level_of_detail"] + 1
                                )
                                changed = True
                            break

    # delete all edges that have a source or target node with a level of detail higher than the level of detail selected by the user
    for edge in edges[:]:
        for node in nodes:
            if (
                node["data"]["id"] == edge["data"]["source"]
                or node["data"]["id"] == edge["data"]["target"]
            ):
                if node["level_of_detail"] > level_of_detail:
                    edges.remove(edge)
                    break

    # delete all nodes that have a level of detail higher than the level of detail selected by the user
    for node in nodes[:]:
        if node["level_of_detail"] > level_of_detail:
            nodes.remove(node)

    # add class to edges that specify the aggregation type such that they can be styled differently in the stylesheet
    for edge in edges:
        if edge["data"]["source"] in aggregation_level_3:
            edge["classes"] = "aggregation_step_3"
        elif edge["data"]["source"] in aggregation_level_2:
            edge["classes"] = "aggregation_step_2"
        elif edge["data"]["source"] in aggregation_level_1:
            edge["classes"] = "aggregation_step_1"

    return nodes, edges


def elements_after_collapse(collapsed_nodes, nodes, edges):
    """Creates the list of all nodes and edges after collapsing the children of the selected node.

    Parameters
    ----------
    collapsed_nodes: list
        The list of all collapsed nodes.
    nodes: list
        The list of all nodes.
    edges: list
        The list of all edges.

    Returns
    -------
    list
        The list of all nodes and edges after collapsing the children of the selected node.
    """

    nodes_after_collapse = nodes[:]
    edges_after_collapse = edges[:]

    def remove_children(node_id):
        """Removes the children of a node and the corresponding edges. Iteratively removes the children of the children.

        Parameters
        ----------
        node_id: str
            The id of the node, whose children should be removed.

        Returns
        -------
        list
            The list of all nodes and edges after removing the children of the selected node.
        """

        for edge in edges_after_collapse[:]:
            if edge["data"]["source"] == node_id:
                edges_after_collapse.remove(edge)
                remove_children(edge["data"]["target"])
                child_node = next(
                    (
                        node
                        for node in nodes_after_collapse
                        if node["data"]["id"] == edge["data"]["target"]
                    ),
                    None,
                )
                nodes_after_collapse.remove(child_node)

    for node in collapsed_nodes:
        remove_children(node)

    # for the nodes that are in the collapsed_list and are collapsible, add a new entry along with data and position called "classes" with the value "collapsed"
    # this is used in the stylesheet to style the collapsed nodes differently
    for node in nodes_after_collapse:
        if node["data"]["id"] in collapsed_nodes and node["collapsible"]:
            node["classes"] += " collapsed"
        else:
            node["classes"] += " not-collapsed"

    return nodes_after_collapse + edges_after_collapse


def create_legend(sector):
    """Creates the legend of the aggregation graph.

    Parameters
    ----------
    sector: str
        The sector of the aggregation graph.

    Returns
    -------
    dbc.Row
        The legend of the aggregation graph."""

    legend = [dbc.Col(html.H6("Aggregation Steps"))]

    if sector == "pow":
        aggregation_step_1 = "Fuel Type (eg. hydrogen, diesel, gasoline, ...)"
        aggregation_step_2 = None
        aggregation_step_3 = None
    elif sector == "tra":
        aggregation_step_1 = (
            "Distance Type (eg: national, european, ...)"
        )
        aggregation_step_2 = "Vehicle Size (eg. small, medium, large, ...)"
        aggregation_step_3 = "Fuel Type (eg. hydrogen, diesel, gasoline, ...)"
    elif sector == "x2x":
        aggregation_step_1 = "Technology Type"
        aggregation_step_2 = None
        aggregation_step_3 = None
    elif sector == "ind":
        aggregation_step_1 = "Process Route"
        aggregation_step_2 = None
        aggregation_step_3 = None
    elif sector == "hea":
        aggregation_step_1 = "Building Type"
        aggregation_step_2 = "Fuel Type (eg. hydrogen, diesel, gasoline, ...)"
        aggregation_step_3 = None

    # size should be 9 for one aggregation step, 4 for two aggregation steps and 3 for three aggregation steps
    if aggregation_step_3 is not None and aggregation_step_2 is not None:
        size = 3
    elif aggregation_step_2 is not None:
        size = 4
    else:
        size = 9

    if aggregation_step_3 is not None:
        legend.append(
            dbc.Col(
                [
                    html.Div(
                        [
                            html.Div(
                                style={
                                    "width": "15px",
                                    "height": "15px",
                                    "background-color": "red",
                                    "display": "inline-block",
                                    "margin-right": "5px",
                                }
                            ),
                            html.Span(
                                aggregation_step_3,
                                style={"font-size": "14px"},
                            ),
                        ]
                    ),
                ],
                width={"size": size},
            ),
        )

    if aggregation_step_2 is not None:
        legend.append(
            dbc.Col(
                [
                    html.Div(
                        [
                            html.Div(
                                style={
                                    "width": "15px",
                                    "height": "15px",
                                    "background-color": "blue",
                                    "display": "inline-block",
                                    "margin-right": "5px",
                                }
                            ),
                            html.Span(
                                aggregation_step_2,
                                style={"font-size": "14px"},
                            ),
                        ]
                    ),
                ],
                width={"size": size},
            ),
        )

    if aggregation_step_1 is not None:
        legend.append(
            dbc.Col(
                [
                    html.Div(
                        [
                            html.Div(
                                style={
                                    "width": "15px",
                                    "height": "15px",
                                    "background-color": "green",
                                    "display": "inline-block",
                                    "margin-right": "5px",
                                }
                            ),
                            html.Span(
                                aggregation_step_1,
                                style={"font-size": "14px"},
                            ),
                        ]
                    ),
                ],
                width={"size": size},
            ),
        )

        return dbc.Row(legend)


def create_tree(elements):
    """Creates the tree graph as a dash component.

    Parameters
    ----------
    elements: list
        The list of all nodes and edges.

    Returns
    -------
    html.Div
        The tree graph and the legend."""

    # get the first three letters of the first node for the sector
    sector = elements[0]["data"]["id"][:3]

    legend = create_legend(sector)

    layout = (
        dbc.Row(html.Div(legend, id="aggregation-legnd")),
        # dbc.Row(
        #     html.H6("Tip: Click node to collapse/expand it (orange node is collapsed)")
        # ),
        dbc.Row(
            html.Div(
                [
                    cyto.Cytoscape(
                        id="cytoscape-tree",
                        layout={"name": "preset", "zoom": 0.2},
                        style={"width": "100%", "height": "800px"},
                        stylesheet=[
                            {
                                "selector": "node",
                                "style": {
                                    "label": "data(id)",
                                    "font-size": "100",
                                    "width": "75",
                                    "height": "75",
                                },
                            },
                            {
                                "selector": ".aggregation_level_1",
                                "style": {"background-color": "green"},
                            },
                            {
                                "selector": ".aggregation_level_2",
                                "style": {"background-color": "blue"},
                            },
                            {
                                "selector": ".aggregation_level_3",
                                "style": {"background-color": "red"},
                            },
                            {
                                "selector": ".collapsed",
                                "style": {"background-color": "orange"},
                            },
                            {
                                "selector": ".aggregation_step_1",
                                "style": {"line-color": "green"},
                            },
                            {
                                "selector": ".aggregation_step_2",
                                "style": {"line-color": "blue"},
                            },
                            {
                                "selector": ".aggregation_step_3",
                                "style": {"line-color": "red"},
                            },
                        ],
                        elements=elements,
                    )
                ]
            )
        ),
    )

    return html.Div(layout)

#
# def collapse_expand_callback(app, collapsed_nodes, file):
#     """Creates the callback function for the aggregation graph.
#
#     Parameters
#     ----------
#     app: dash.Dash
#         The dash application.
#     collapsed_nodes: list
#         The list of all collapsed nodes.
#     file: str
#         The path to the Excel file of the Model Structure.
#     """
#
#     @app.callback(
#         Output("cytoscape-tree", "elements", allow_duplicate=True),
#         Input("cytoscape-tree", "selectedNodeData"),
#         Input("aggregation-slider", "value"),
#         Input("aggregation-sector", "value"),
#         State("cytoscape-tree", "elements"),
#         prevent_initial_call=True,
#     )
#     def update_aggregation_graph(nodeData, value, sector, elements):
#         """Collapses or expands the children of the the selected node.
#
#         Parameters
#         ----------
#         nodeData: list
#             The list of all selected nodes.
#         value: int
#             The aggregation level.
#         sector: str
#             The sector of the aggregation graph.
#         elements: list
#             The list of all nodes and edges.
#
#         Returns
#         -------
#         list
#             The updated list of all nodes and edges."""
#
#         level_of_detail = value
#
#         if not nodeData:
#             return elements
#
#         node_id = nodeData[0]["id"]
#
#         if node_id in collapsed_nodes:
#             collapsed_nodes.remove(node_id)
#         else:
#             collapsed_nodes.append(node_id)
#
#         nodes, edges = generate_elements(file, level_of_detail, sector)
#
#         updated_elements = elements_after_collapse(collapsed_nodes, nodes, edges)
#         return updated_elements

#
# def detail_level_callback(app, file, collapsed_nodes):
#     """Creates the callback function for the aggregation level slider.
#
#     Parameters
#     ----------
#     app: dash.Dash
#         The dash application.
#     file: str
#         The path to the Excel file of the Model Structure.
#     collapsed_nodes: list
#         The list of all collapsed nodes."""
#
#     @app.callback(
#         [Output("cytoscape-tree", "elements"), Output("aggregation-legnd", "children")],
#         [Input("aggregation-slider", "value"), Input("aggregation-sector", "value")],
#     )
#     def update_detail_level(value, sector):
#         """Updates the detail level of the aggregation graph.
#
#         Parameters
#         ----------
#         value: int
#             The detail level.
#         sector: str
#             The sector of the aggregation graph.
#
#         Returns
#         -------
#         list
#             The filtered list of all nodes and edges.
#         """
#         level_of_detail = value
#
#         # create nodes and edges
#         nodes, edges = generate_elements(file, level_of_detail, sector)
#
#         collapsed_nodes.clear()
#
#         # elements that are to be displayed after collapsing
#         elements = elements_after_collapse(collapsed_nodes, nodes, edges)
#
#         # create legend
#         legend = create_legend(sector)
#
#         return elements, legend