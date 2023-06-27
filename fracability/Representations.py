
# THIS NEEDS A DO-OVER

import geopandas
import networkx
import numpy as np
from pyvista import PolyData, lines_from_points

from vtkmodules.vtkFiltersCore import vtkAppendPolyData

import networkx as nx
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter

from fracability.operations.Cleaners import connect_dots


def node_vtk_rep(input_df: geopandas.GeoDataFrame) -> PolyData:

    points = np.array([point.coords for point in input_df.geometry]).reshape(-1, 3)
    types = input_df['type'].values
    node_types = input_df['node_type'].values

    points_vtk = PolyData(points)
    points_vtk['type'] = types
    points_vtk['node_type'] = node_types

    return points_vtk


def frac_vtk_rep(input_df: geopandas.GeoDataFrame) -> PolyData:
    appender = vtkAppendPolyData()

    for index, geom, set_n in zip(input_df.index, input_df['geometry'],
                                  input_df['set']):  # For each geometry in the df

        x, y = geom.coords.xy  # get xy as an array
        z = np.zeros_like(x)  # create a zeros z array with the same dim of the x (or y)

        points = np.stack((x, y, z), axis=1)  # Stack the coordinates to a [n,3] shaped array
        # offset = np.round(points[0][0])
        pv_obj = lines_from_points(points)  # Create the corresponding vtk line with the given points
        pv_obj.cell_data['type'] = ['fracture'] * pv_obj.GetNumberOfCells()
        pv_obj.point_data['type'] = ['fracture'] * pv_obj.GetNumberOfPoints()

        pv_obj.cell_data['set'] = [set_n] * pv_obj.GetNumberOfCells()
        pv_obj.point_data['set'] = [set_n] * pv_obj.GetNumberOfPoints()

        pv_obj['RegionId'] = [index] * pv_obj.GetNumberOfPoints()

        # line.plot()

        appender.AddInputData(pv_obj)  # Add the new object

    geometry_filter = vtkGeometryFilter()
    geometry_filter.SetInputConnection(appender.GetOutputPort())
    geometry_filter.Update()

    output_obj = PolyData(geometry_filter.GetOutput())
    conn_obj = connect_dots(output_obj)

    return conn_obj


def bound_vtk_rep(input_df: geopandas.GeoDataFrame) -> PolyData:

    appender = vtkAppendPolyData()

    for index, geom in zip(input_df.index, input_df['geometry']):  # For each geometry in the df

        x, y = geom.coords.xy  # get xy as an array
        z = np.zeros_like(x)  # create a zeros z array with the same dim of the x (or y)

        points = np.stack((x, y, z), axis=1)  # Stack the coordinates to a [n,3] shaped array
        # offset = np.round(points[0][0])
        pv_obj = lines_from_points(points)  # Create the corresponding vtk line with the given points
        pv_obj.cell_data['type'] = ['boundary'] * pv_obj.GetNumberOfCells()
        pv_obj.point_data['type'] = ['boundary'] * pv_obj.GetNumberOfPoints()

        pv_obj['RegionId'] = [index] * pv_obj.GetNumberOfPoints()

        # line.plot()

        appender.AddInputData(pv_obj)  # Add the new object

    geometry_filter = vtkGeometryFilter()
    geometry_filter.SetInputConnection(appender.GetOutputPort())
    geometry_filter.Update()

    output_obj = PolyData(geometry_filter.GetOutput())
    conn_obj = connect_dots(output_obj)

    return conn_obj


def fracture_network_rep(input_df: geopandas.GeoDataFrame) -> PolyData:
    nodes_df = input_df.loc[input_df['type'] == 'node']
    fractures_df = input_df.loc[input_df['type'] == 'fracture']
    boundaries_df = input_df.loc[input_df['type'] == 'boundary']

    nodes_vtk = node_vtk_rep(nodes_df)
    fractures_vtk = frac_vtk_rep(fractures_df)
    boundaries_vtk = bound_vtk_rep(boundaries_df)

    appender = vtkAppendPolyData()

    appender.AddInputData(nodes_vtk)
    appender.AddInputData(fractures_vtk)
    appender.AddInputData(boundaries_vtk)

    appender.Update()

    geometry_filter = vtkGeometryFilter()
    geometry_filter.SetInputConnection(appender.GetOutputPort())
    geometry_filter.Update()

    output_obj = PolyData(geometry_filter.GetOutput())
    conn_obj = connect_dots(output_obj)

    return conn_obj


def networkx_rep(input_object: PolyData) -> networkx.Graph:

    network = input_object
    lines = network.lines  # Get the connectivity list of the object

    lines = np.delete(lines,
                      np.arange(0, lines.size, 3))  # remove padding eg. [2 id1 id2 2 id3 id4 ...] -> remove the 2

    test_types = np.array([{'type': t} for t in network['type']])
    edges = np.c_[lines.reshape(-1, 2), test_types]

    network = nx.Graph()  # Create a networkx graph instance

    network.add_edges_from(edges)  # Add the edges

    output_obj = network
    return output_obj


