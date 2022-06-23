from .imports import ImportsView
from .delete import DeleteView
from .nodes import NodesView
from .sales import SalesView
from .node import NodeView

HANDLERS = (ImportsView, DeleteView, NodesView, SalesView, NodeView)
