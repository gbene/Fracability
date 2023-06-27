from copy import deepcopy

from matplotlib import pyplot as plt
from vtkmodules.vtkFiltersCore import vtkConnectivityFilter

from fracability.Entities import BaseEntity, FractureNetwork, Nodes

from shapely.geometry import Point, MultiPoint
from geopandas import GeoDataFrame
from pyvista import PolyData
import numpy as np


def nodes_conn(obj: BaseEntity, inplace=True):

    network_obj = obj.network_object
    vtk_obj = obj.vtk_object
    entity_df_obj = obj.entity_df

    fractures_obj = obj.fractures.vtk_object

    frac_idx = np.where(vtk_obj.point_data['type'] == 'fracture')[0]

    class_list = []
    Y_node_origin = []

    # n_nodes = vtk_obj.n_points
    node_geometry = []
    for node in frac_idx:  # For each node of the fractures:
        # print(f'Classifying node {node} of {len(frac_idx)} ', end='\r')

        n_edges = network_obj.degree[node]  # Calculate number of connected nodes

        point = Point(vtk_obj.points[node])

        if n_edges == 2:  # Exclude internal and V nodes
            n_edges = -9999

        elif n_edges == 3:  # Discriminate Y and U nodes

            cells = vtk_obj.extract_points(node)

            if 'boundary' in cells.cell_data['type']:

                n_edges = 5
                index = vtk_obj['RegionId'][node]
                entity_df_obj.loc[index, 'censored'] = 1

            else:

                cells = fractures_obj.extract_points(node)
                tuple_set = tuple(set(cells.cell_data['set']))
                Y_node_origin.append(tuple_set)

        elif n_edges > 4:
            n_edges = -9999

        node_geometry.append(point)
        class_list.append(n_edges)  # Append the value (number of connected nodes)

    obj.entity_df = entity_df_obj

    class_list = np.array(class_list)

    indexes = np.where(class_list >= 0)[0]

    node_geometry = [node_geometry[index] for index in indexes]
    class_list = class_list[indexes]

    entity_df = GeoDataFrame({'type': 'node', 'node_type': class_list, 'Y_node_origin': '',
                              'geometry': node_geometry}, crs=entity_df_obj.crs)

    for i, Y_origin in zip(entity_df.loc[entity_df['node_type']==3].index, Y_node_origin):
        entity_df.at[i, 'Y_node_origin'] = Y_origin

    fracture_nodes = Nodes(entity_df)

    if inplace:

        if obj.name == 'Fractures':
            new_fracture_net = FractureNetwork()

            new_fracture_net.fractures = obj
            new_fracture_net.nodes = fracture_nodes

            return new_fracture_net

        else:
            obj.nodes = fracture_nodes

            return obj

    else:
        return fracture_nodes


def find_backbone(obj: FractureNetwork) -> PolyData:

    fractures = obj.fractures.vtk_object

    connectivity = vtkConnectivityFilter()

    connectivity.AddInputData(fractures)
    connectivity.SetExtractionModeToLargestRegion()
    connectivity.Update()

    backbone = PolyData(connectivity.GetOutput())

    return backbone
