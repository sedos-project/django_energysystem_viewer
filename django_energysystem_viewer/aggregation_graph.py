from openpyxl import load_workbook
import pandas as pd


def generate_aggregation_graph(df_aggregation_mapping, sectors, lod, process_list):
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
    sector = sectors

    nodes, edges = generate_elements(df_aggregation_mapping, lod, sector, process_list)
    elements = elements_after_collapse(collapsed_nodes, nodes, edges)

    return elements


def get_aggregation_level(target_value: int, df: pd.DataFrame) -> list:
    """
    Returns a list of all processes of one aggregation level.

    Parameters
    ----------
    target_value: int
        The target value to compare.
    df: pd.DataFrame
        The DataFrame of the Model Structure.

    Returns
    -------
    list
        The list of elements of the corresponding aggregation level.
    """
    elements = []

    for _, row in df.iterrows():
        for idx in range(2):
            compare_cell_value = row.iloc[idx + 2]
            if compare_cell_value == target_value:
                elements.append(row.iloc[idx])

    # Remove duplicates while preserving order
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


def generate_elements(df_aggregation_mapping, level_of_detail, sector, process_list):
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
    lod_levels = [3, 2, 1, 0]
    aggregation_levels = {}
    none_items = []
    for n in lod_levels:
        aggregation_levels[n] = []
        for item in get_aggregation_level(n, df_aggregation_mapping):
            if item is None:
                none_items.append(item)
            elif item.startswith(sector):
                aggregation_levels[n].append(item)
    # print("Count of None items:", len(none_items))
    agg_list = sum(aggregation_levels.values(), [])
    process_list_sector = [item for item in process_list if item.startswith(sector)]

    # Those processes which are in the Process_Set but are not in the Aggregation_Mapping are added to the list
    no_agg_list = list(set(process_list_sector) - set(agg_list))
    aggregation_levels[0] = aggregation_levels[0] + no_agg_list
    agg_list = agg_list + no_agg_list
    nodes = create_nodes(agg_list, aggregation_levels, level_of_detail)
    edges = create_edges(df_aggregation_mapping, agg_list, sector, nodes, aggregation_levels, level_of_detail)
    return nodes, edges

def generate_df_lod(df_aggregation_mapping, lod, process_list):
    """Returns a dataframe where columns denote sectors and rows its related processes for a chosen level of detail (lod).

    Parameters
    ----------
    file: str
        The path to the Excel file of the Model Structure.
    lod: int
        The level of detail chosen by the user.
    process_list: list
        The list of all processes from the Process_Set.

    Returns
    -------
    dataframe
        All processes for a certain level of detail.
    """
    df_lod = pd.DataFrame()

    sectors = ["pow", "x2x", "hea", "ind", "tra"]
    for sector in sectors:
        nodes, edges = generate_elements(df_aggregation_mapping, lod, sector, process_list)
        edge_sources_list = [item['data']['source'] for item in edges]
        lod_list = [item['data']['id'] for item in nodes if item['data']['id'] not in edge_sources_list]
        df_lod = pd.concat([df_lod, pd.Series(lod_list, name=sector)], axis=1)
    return df_lod

def create_nodes(agg_list, aggregation_levels, level_of_detail):
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

    for node in agg_list:
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


def create_edges(df_aggregation_mapping, agg_list, sector, nodes, aggregation_levels, level_of_detail):
    """Creates the edges for the aggregation graph.

    Parameters
    ----------
    df_aggregation_mapping: Dataframe
        The dataframe with the aggregation mapping
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

    for idx, row in df_aggregation_mapping.iterrows():
        source = row.iloc[0]
        target = row.iloc[1]

        if source in agg_list and target in agg_list:
            edges.append({"data": {"source": source, "target": target}})
            for node in nodes:
                if node["data"]["id"] == source:
                    node["collapsible"] = True
                    break
        elif pd.isna(source) and not pd.isna(target):
            i = idx - 1
            while pd.isna(df_aggregation_mapping.iloc[i, 0]):
                i -= 1
            source = df_aggregation_mapping.iloc[i, 0]
            if source in agg_list and target in agg_list:
                edges.append({"data": {"source": source, "target": target}})

    nodes.append({
        "data": {"id": sector, "label": sector},
        "position": {"x": 0, "y": 0},
        "classes": "not-collapsed",
        "collapsible": True,
        "level_of_detail": 0,
    })

    for node in agg_list:
        if not any(edge["data"]["target"] == node for edge in edges):
            edges.append({"data": {"source": sector, "target": node}})

    assign_levels(nodes, edges)

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