import nodeitems_utils

class GP2DMorphsNodeCategory(nodeitems_utils.NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type in {'GP2DMorphsNodeTree', 'GP2DMorphsNodeTreeGroup'}

node_categories = [
    GP2DMorphsNodeCategory("MORPH", "Morphs", items=[
        nodeitems_utils.NodeItem("GP2DMorphsNodeGP2DMorph"),
        nodeitems_utils.NodeItem("GP2DMorphsNodeBoneMorph"),
    ]),
    GP2DMorphsNodeCategory("CONTROL", "Controls", items=[
        nodeitems_utils.NodeItem('GP2DMorphsNodeControlLocation'),
        nodeitems_utils.NodeItem('GP2DMorphsNodeControlRotation'),
    ]),
    GP2DMorphsNodeCategory("INPUT", "Input", items=[
        nodeitems_utils.NodeItem('GP2DMorphsNodeIntInput'),
    ]),

]


def register():
    try:
        nodeitems_utils.unregister_node_categories("GP2DMorphsNodeCategory")
    except Exception:
        pass
    nodeitems_utils.register_node_categories("GP2DMorphsNodeCategory", node_categories)


def unregister():
    nodeitems_utils.unregister_node_categories("GP2DMorphsNodeCategory")
