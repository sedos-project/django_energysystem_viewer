document.addEventListener('DOMContentLoaded', function() {
    var nodesData = JSON.parse('{{nodes|safe}}');
    var edgesData = JSON.parse('{{edges|safe}}');

    var cy = cytoscape({
        container: document.getElementById('cytoscape-container'),
        elements: {
            nodes: nodesData,
            edges: edgesData
        },
        style: [ 
        {
            selector: "node",
            style: {
                "label": "data(id)",
                "font-size": "100",
                "width": "125",
                "height": "125"
            }
        },
        {
            selector: ".collapsed",
            style: {"background-color": "red"}
        },
        {
            selector: ".aggregation_step_1",
            style: {"line-color": "green"}
        },
        {
            selector: ".aggregation_step_2",
            style: {"line-color": "blue"}
        },
        {
            selector: ".aggregation_step_3",
            style: {"line-color": "red"}
        }]
    });
});