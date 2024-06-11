from openpyxl import load_workbook


def generate_aggregation_graph(file, sectors, lod):
    """Generates the aggregation graph as a dash component using the functions below.

    Parameters
    ----------
    file: str
        The path to the Excel file of the Model Structure.
    sectors: str
        The sector to filter the aggregation levels.
    lod: int
        The desired level of detail.

    Returns
    -------
    list
        The aggregation graph elements (nodes and edges).
    """
    collapsed_nodes = []
    level_of_detail = int(lod)
    sector = sectors

    nodes, edges = generate_elements(file, level_of_detail, sector)
    elements = elements_after_collapse(collapsed_nodes, nodes, edges)

    return elements


def get_aggregation_level(target_value, sheet):
    """Returns a list of all processes of one aggregation level according to the background color of the corresponding cell.

    Parameters
    ----------
    target_value: int
        The target value to compare.
    sheet: str
        The sheet of the Excel file of the Model Structure.

    Returns
    -------
    list
        The list of elements of the corresponding aggregation level.
    """
    elements = []

    for row in sheet.iter_rows(min_row=2, min_col=1, max_col=4):
        for idx, cell in enumerate(row):
            if idx < 2:
                compare_cell_value = row[idx + 2].value
                if compare_cell_value == target_value:
                    elements.append(cell.value)

    return list(dict.fromkeys(elements))


def calc_pos(node, aggregation_levels, level_of_detail):
    """Assigns the position of a node according to its aggregation level.

    Parameters
    ----------
    node: str
        The node for which a position should be assigned.
    aggregation_levels: dict
        The dictionary of filtered aggregation levels.
    level_of_detail: int
        The desired level of detail.

    Returns
    -------
    int
        The x-coordinate of the node.
    int
        The y-coordinate of the node.
    """
    scaling_factor_x = 2000
    scaling_factor_y = 150

    for level, processes in aggregation_levels.items():
        if node in processes:
            N = len(processes)
            span = N * scaling_factor_y
            y = processes.index(node) * scaling_factor_y - span / 2
            x = (4 - level) * scaling_factor_x
            return x, y
    return 0, 0


def generate_elements(file, level_of_detail, sector):
    """Generates the nodes and edges of the aggregation graph.

    Parameters
    ----------
    file: str
        The path to the Excel file of the Model Structure.
    level_of_detail: int
        The desired level of detail.
    sector: str
        The sector to filter the aggregation levels.

    Returns
    -------
    list
        The list of all nodes.
    list
        The list of all edges.
    """
    wb = load_workbook(file)
    sheet = wb["Aggregation_Mapping"]

    aggregation_levels = {
        3: [item for item in get_aggregation_level(3, sheet) if item.startswith(sector)],
        2: [item for item in get_aggregation_level(2, sheet) if item.startswith(sector)],
        1: [item for item in get_aggregation_level(1, sheet) if item.startswith(sector)],
        0: [item for item in get_aggregation_level(0, sheet) if item.startswith(sector)]
    }

    process_list = sum(aggregation_levels.values(), [])
    nodes = create_nodes(process_list, aggregation_levels, level_of_detail)
    edges = create_edges(sheet, process_list, sector, nodes, aggregation_levels, level_of_detail)

    return nodes, edges


def create_nodes(process_list, aggregation_levels, level_of_detail):
    """Creates the nodes for the aggregation graph.

    Parameters
    ----------
    process_list: list
        The list of all processes.
    aggregation_levels: dict
        The dictionary of filtered aggregation levels.
    level_of_detail: int
        The desired level of detail.

    Returns
    -------
    list
        The list of nodes.
    """
    nodes = []

    for node in process_list:
        x, y = calc_pos(node, aggregation_levels, level_of_detail)
        nodes.append({
            "data": {"id": node, "label": node},
            "position": {"x": x, "y": y},
            "classes": "",
            "collapsible": False,
            "level_of_detail": -1,
        })

    for node in nodes:
        for level, processes in aggregation_levels.items():
            if node["data"]["id"] in processes:
                node["classes"] = f"aggregation_level_{level}"

    return nodes


def create_edges(sheet, process_list, sector, nodes, aggregation_levels, level_of_detail):
    """Creates the edges for the aggregation graph.

    Parameters
    ----------
    sheet: object
        The sheet object of the Excel file.
    process_list: list
        The list of all processes.
    sector: str
        The sector to filter the aggregation levels.
    nodes: list
        The list of nodes.
    aggregation_levels: dict
        The dictionary of filtered aggregation levels.

    Returns
    -------
    list
        The list of edges.
    """
    edges = []

    for row in sheet.iter_rows(min_row=2, min_col=1, max_col=1):
        for cell in row:
            if cell.value in process_list and cell.offset(column=1).value in process_list:
                edges.append({"data": {"source": cell.value, "target": cell.offset(column=1).value}})
                for node in nodes:
                    if node["data"]["id"] == cell.value:
                        node["collapsible"] = True
                        break
            elif cell.value is None and cell.offset(column=1).value is not None:
                i = 1
                while cell.offset(row=-i).value is None:
                    i += 1
                if cell.offset(row=-i).value in process_list and cell.offset(column=1).value in process_list:
                    edges.append({"data": {"source": cell.offset(row=-i).value, "target": cell.offset(column=1).value}})

    nodes.append({
        "data": {"id": sector, "label": sector},
        "position": {"x": 0, "y": 0},
        "classes": "not-collapsed",
        "collapsible": True,
        "level_of_detail": 0,
    })

    for node in process_list:
        if not any(edge["data"]["target"] == node for edge in edges):
            edges.append({"data": {"source": sector, "target": node}})

    assign_levels(nodes, edges)
    filter_elements(nodes, edges, level_of_detail)

    for edge in edges:
        for level in range(3, 0, -1):
            if edge["data"]["source"] in aggregation_levels[level]:
                edge["classes"] = f"aggregation_step_{level}"
                break

    return edges


def assign_levels(nodes, edges):
    """Assign levels to nodes based on their connections.

    Parameters
    ----------
    nodes: list
        The list of nodes.
    edges: list
        The list of edges.
    """
    changed = True
    while changed:
        changed = False
        for edge in edges:
            source_node = next(node for node in nodes if node["data"]["id"] == edge["data"]["source"])
            target_node = next(node for node in nodes if node["data"]["id"] == edge["data"]["target"])
            if source_node["level_of_detail"] != -1 and target_node["level_of_detail"] != source_node["level_of_detail"] + 1:
                target_node["level_of_detail"] = source_node["level_of_detail"] + 1
                changed = True


def filter_elements(nodes, edges, level_of_detail):
    """Filters out elements based on the level of detail.

    Parameters
    ----------
    nodes: list
        The list of nodes.
    edges: list
        The list of edges.
    level_of_detail: int
        The desired level of detail.
    """
    edges[:] = [edge for edge in edges if all(
        node["level_of_detail"] <= level_of_detail
        for node in nodes
        if node["data"]["id"] in (edge["data"]["source"], edge["data"]["target"])
    )]

    nodes[:] = [node for node in nodes if node["level_of_detail"] <= level_of_detail]


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
        for edge in edges_after_collapse[:]:
            if edge["data"]["source"] == node_id:
                edges_after_collapse.remove(edge)
                remove_children(edge["data"]["target"])
                child_node = next((node for node in nodes_after_collapse if node["data"]["id"] == edge["data"]["target"]), None)
                if child_node:
                    nodes_after_collapse.remove(child_node)

    for node in collapsed_nodes:
        remove_children(node)

    for node in nodes_after_collapse:
        if node["data"]["id"] in collapsed_nodes and node["collapsible"]:
            node["classes"] += " collapsed"
        else:
            node["classes"] += " not-collapsed"

    return nodes_after_collapse + edges_after_collapse