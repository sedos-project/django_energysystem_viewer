from django.test import TestCase

from django_energysystem_viewer import network_graph


class TestProcesses(TestCase):
    def test_get_processes(self):
        processes = network_graph.get_processes()
        assert len(processes) == 1226


class TestCommodities(TestCase):
    def test_get_commodities(self):
        commodities = network_graph.get_commodities([])
        assert len(commodities) == 0
        commodities = network_graph.get_commodities(["pow"])
        assert len(commodities) == 22
        commodities = network_graph.get_commodities(["x2x"])
        assert len(commodities) == 25
        commodities = network_graph.get_commodities(["hea"])
        assert len(commodities) == 78
        commodities = network_graph.get_commodities(["ind"])
        assert len(commodities) == 125
        commodities = network_graph.get_commodities(["mob"])
        assert len(commodities) == 54
        commodities = network_graph.get_commodities(["pow", "x2x", "hea", "ind", "mob"])
        assert len(commodities) == 253
