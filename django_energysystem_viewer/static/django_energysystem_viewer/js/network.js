// Variables to store click information and original styles
var previousHighlights = []; // To keep track of previously highlighted elements
var originalStyles = {
  nodeColors: {},
  nodeSizes: {},
  edgeColors: {},
  edgeWidths: {},
  edgeDashes: {}
};
var graphDiv; // To store the graphDiv for use in functions

// Function to attach click events
function attachPlotlyClickEvents(graphDiv) {
  // Initialize originalStyles
  originalStyles = {
    nodeColors: {},
    nodeSizes: {},
    edgeColors: {},
    edgeWidths: {},
    edgeDashes: {}
  };

  graphDiv.data.forEach(function(trace, traceIndex) {
    if (trace.mode && trace.mode.includes('markers')) {
      // Nodes
      var numPoints = trace.x.length;
      var markerColor = trace.marker.color;
      var markerSize = trace.marker.size;

      // Ensure markerColor and markerSize are arrays
      var colors = [];
      var sizes = [];

      for (var i = 0; i < numPoints; i++) {
        colors.push(Array.isArray(markerColor) ? markerColor[i] : markerColor);
        sizes.push(Array.isArray(markerSize) ? markerSize[i] : markerSize);
      }

      // Store original marker colors and sizes
      originalStyles.nodeColors[traceIndex] = colors;
      originalStyles.nodeSizes[traceIndex] = sizes;
    } else if (trace.mode && trace.mode.includes('lines')) {
      // Edges
      // Store original line colors, widths, and dashes
      originalStyles.edgeColors[traceIndex] = trace.line.color;
      originalStyles.edgeWidths[traceIndex] = trace.line.width;
      originalStyles.edgeDashes[traceIndex] = trace.line.dash || 'solid';
    }
  });

  // Handle click events
  graphDiv.on('plotly_click', function(data) {
    var point = data.points[0];
    var traceIndex = point.fullData.index;
    var pointIndex = point.pointIndex;
    var nodeData = point.customdata;

    // Reset highlights first
    resetHighlights(graphDiv);

    if (point.data.mode && point.data.mode.includes('lines')) {
      // Edge Clicked
      var edgeTraceIndex = traceIndex;
      highlightConnectedElements(graphDiv, null, null, edgeTraceIndex);
    } else if (nodeData) {
      // Node Clicked
      var nodeId = nodeData.node_id;
      highlightConnectedElements(graphDiv, nodeId);
    }
  });

  // Handle click events on the background to reset highlights
  graphDiv.on('plotly_clickannotation', function(event) {
    // Clicked on an annotation (background), reset highlights
    resetHighlights(graphDiv);
  });

  // Optionally, handle double-click to reset highlights
  graphDiv.on('plotly_doubleclick', function(event) {
    resetHighlights(graphDiv);
  });
}

function highlightConnectedElements(graphDiv, nodeId = null, connectedNodeIds = null, edgeTraceIndex = null) {
  var data = graphDiv.data;
  var nodesToHighlight = new Set();
  var edgesToHighlight = new Set();

  if (nodeId) {
    // Node is clicked
    nodesToHighlight.add(nodeId);

    // Find connected nodes and edges
    data.forEach(function(trace, traceIndex) {
      if (trace.mode && trace.mode.includes('lines')) {
        // Edges
        var edgeData = trace.customdata[0];
        if (edgeData && (edgeData.source === nodeId || edgeData.target === nodeId)) {
          edgesToHighlight.add(traceIndex);
          // Add connected nodes
          nodesToHighlight.add(edgeData.source);
          nodesToHighlight.add(edgeData.target);
        }
      }
    });
  } else if (edgeTraceIndex !== null) {
    // Edge is clicked
    edgesToHighlight.add(edgeTraceIndex);
    var edgeData = data[edgeTraceIndex].customdata[0];
    if (edgeData) {
      nodesToHighlight.add(edgeData.source);
      nodesToHighlight.add(edgeData.target);
    }
  }

  // Highlight nodes
  data.forEach(function(trace, traceIndex) {
    if (trace.mode && trace.mode.includes('markers')) {
      var nodeIds = trace.customdata.map(cd => cd.node_id);
      var newColors = originalStyles.nodeColors[traceIndex].slice();
      var newSizes = originalStyles.nodeSizes[traceIndex].slice();

      for (var i = 0; i < nodeIds.length; i++) {
        if (nodesToHighlight.has(nodeIds[i])) {
          if (nodeId && nodeIds[i] === nodeId) {
            // Clicked node
            newColors[i] = 'red';
            newSizes[i] = 10;
          } else {
            // Connected nodes
            newColors[i] = 'orange';
            newSizes[i] = 9;
          }
        }
      }

      // Update the trace
      Plotly.restyle(graphDiv, {
        'marker.color': [newColors],
        'marker.size': [newSizes]
      }, [traceIndex]);

      // Store for reset
      previousHighlights.push({type: 'node', traceIndex: traceIndex});
    }
  });

  // Highlight edges
  edgesToHighlight.forEach(function(edgeIndex) {
    var originalDash = originalStyles.edgeDashes[edgeIndex];
    var color = (edgeIndex === edgeTraceIndex) ? 'red' : 'orange';
    var width = (edgeIndex === edgeTraceIndex) ? 4 : 3;

    Plotly.restyle(graphDiv, {
      'line.color': color,
      'line.width': width,
      'line.dash': originalDash // Preserve the original dash style
    }, [edgeIndex]);

    // Store for reset
    previousHighlights.push({type: 'edge', traceIndex: edgeIndex});
  });
}

function resetHighlights(graphDiv) {
  previousHighlights.forEach(function(item) {
    if (item.type === 'node') {
      var traceIndex = item.traceIndex;
      var originalColors = originalStyles.nodeColors[traceIndex];
      var originalSizes = originalStyles.nodeSizes[traceIndex];

      Plotly.restyle(graphDiv, {
        'marker.color': [originalColors],
        'marker.size': [originalSizes]
      }, [traceIndex]);
    } else if (item.type === 'edge') {
      var traceIndex = item.traceIndex;
      var originalColor = originalStyles.edgeColors[traceIndex];
      var originalWidth = originalStyles.edgeWidths[traceIndex];
      var originalDash = originalStyles.edgeDashes[traceIndex];

      Plotly.restyle(graphDiv, {
        'line.color': originalColor,
        'line.width': originalWidth,
        'line.dash': originalDash
      }, [traceIndex]);
    }
  });
  previousHighlights = [];
}

// Initial attachment of click events when the page loads
document.addEventListener('DOMContentLoaded', function() {
  graphDiv = document.getElementById('network_graph').getElementsByClassName('js-plotly-plot')[0];
  if (graphDiv) {
    attachPlotlyClickEvents(graphDiv);
  }
});

// Reattach click events after HTMX updates the content
document.addEventListener('htmx:afterSettle', function(event) {
  if (event.target.id === 'network_graph') {
    console.log('htmx:afterSettle - reattaching click events');
    var targetNode = document.getElementById('network_graph');
    // Use a MutationObserver to detect when the graph is rendered
    var observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.type === 'childList') {
          graphDiv = targetNode.getElementsByClassName('js-plotly-plot')[0];
          if (graphDiv) {
            console.log('GraphDiv found via MutationObserver');
            attachPlotlyClickEvents(graphDiv);
            observer.disconnect();
          }
        }
      });
    });
    observer.observe(targetNode, { childList: true, subtree: true });
  }
});