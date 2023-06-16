"""
In general, it would be good to give the possibility to trat separately sets of fractures/different types of nodes/
boundary and then everything together to consider the network as a compostion of single entities and not as a single
entity.

"""

from geopandas import GeoDataFrame
import pandas as pd
from shapely.geometry import MultiLineString, Polygon, LineString, Point
from pyvista import PolyData, DataSet
from networkx import Graph
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter

import fracability.Representations as Rep
from abc import ABC, abstractmethod


class BaseEntity(ABC):
    """
    Abstract class for Fracture network entities:

    1. Nodes
    2. Fractures
    3. Boundaries
    4. Fracture Networks
    """

    def __init__(self, gdf: GeoDataFrame = None):
        """
        Init the entity. If a geopandas dataframe is specified then it is
        set as the source entity df.

        :param gdf: Geopandas dataframe
        """

        self._df = None
        self._vtk_obj = None
        self._network_obj = None
        if gdf is not None:
            self.entity_df = gdf

    # @abstractmethod
    # def _process_df(self):
    #     """
    #     Each entity process the input dataframe in different ways
    #     (for example boundaries vs. fractures).
    #     Use this method to define the pipeline used to parse the dataframe
    #     :return:
    #     """
    #
    #     pass

    def _process_vtk(self):
        """
        Each entity process the vtk objects in different ways (for example frac net vs fractures).
        Use this method to define the pipeline for the vtk objects
        """

        pass

    @property
    def entity_df(self) -> GeoDataFrame:
        """
        Each entity is based on a geopandas dataframe. This property returns or sets
        the entity_df of the given entity.

        :getter: Returns the GeoDataFrame
        :setter: Sets the GeoDataFrame
        :type: GeoDataFrame

        Notes
        -------
        When set the dataframe is modified to conform to the assigned entity structure.
        """

        return self._df

    @entity_df.setter
    def entity_df(self, gdf: GeoDataFrame):
        pass

    @abstractmethod
    def vtk_object(self) -> PolyData:
        """
        Each entity can be represented with a vtk object.
        This returns a Pyvista PolyData object representing the entity_df.

        :getter: Returns a Pyvista PolyData object
        :setter: Sets a generic Pyvista DataSet
        :type: pyvista PolyData

        Notes
        -------
        When the get method is applied the PolyData is build **on the fly** using the entity_df as a source.

        When set the DataSet is **cast to a PolyData**.
        """
        pass

    @property
    def network_object(self) -> Graph:
        """
        Each entity can be represented with a networkx graph.
        This returns the network object using the vtk object (and so the df).

        :getter: Returns a networkx Graph object
        :setter: Sets a Graph object
        :type: pyvista Graph

        Notes
        -------
        When the get method is applied the Graph is build **on the fly** using the object and so the entity_df.
        """

        obj = Rep.networkx_rep(self.vtk_object)
        return obj

    @network_object.setter
    def network_object(self, obj: Graph):
        """
        Each entity can be represented with a networkx Graph object.
        This sets the graph object.
        """

        self._network_obj = obj


class Nodes(BaseEntity):
    """
    Node base entity, represents all the nodes in the network.
    """
    @property
    def vtk_object(self) -> PolyData:

        df = self.entity_df
        vtk_obj = Rep.point_vtk_rep(df)
        return vtk_obj

    @vtk_object.setter
    def vtk_object(self, obj: DataSet):

        for index, point in enumerate(obj.points):
            self.entity_df.loc[self.entity_df['id'] == index, 'geometry'] = Point(point)

    @BaseEntity.entity_df.setter
    def entity_df(self, gdf: GeoDataFrame):
        """
        Each entity process the input dataframe in different ways
        Nodes modify the entity_df only to add the type column (if not
        already present)
        """

        self._df = gdf

        if 'type' not in self._df.columns:
            self._df['type'] = 'node'
        if 'node_type' not in self._df.columns:
            self._df['node_type'] = -9999

    def _process_vtk(self):
        print(self.vtk_object)
        print(self.entity_df)
        pass


class Fractures(BaseEntity):
    """
    Base entity for fractures
    """

    @property
    def vtk_object(self):
        df = self.entity_df
        vtk_obj = Rep.point_vtk_rep(df)
        return vtk_obj

    @vtk_object.setter
    def vtk_object(self, obj: DataSet):

        for region in set(obj['RegionId']):
            region = obj.extract_points(obj['RegionId'] == region)
            self.entity_df.loc[self.entity_df['id'] == region, 'geometry'] = LineString(region.points)



    @BaseEntity.entity_df.setter
    def entity_df(self, gdf: GeoDataFrame):
        """
        Each entity process the input dataframe in different ways
        Fractures modify the entity_df by adding the 'type' and
        'censored' column (if not already present). The censored column
        is a bool column that identifies if the fracture is censored (1) or
        not (0)
        """

        self._df = gdf
        self._df.reset_index(inplace=True, drop=True)

        if 'type' not in self._df.columns:
            self._df['type'] = 'fracture'
        if 'censored' not in self._df.columns:
            self._df['censored'] = 0


class Boundary(BaseEntity):
    """
    Base entity for boundaries
    """

    @property
    def vtk_object(self):
        df = self.entity_df
        vtk_obj = Rep.point_vtk_rep(df)
        return vtk_obj

    @vtk_object.setter
    def vtk_object(self, obj: DataSet):

        for region in set(obj['RegionId']):
            region = obj.extract_points(obj['RegionId'] == region)
            self.entity_df.loc[self.entity_df['id'] == region, 'geometry'] = LineString(region.points)

    @BaseEntity.entity_df.setter
    def entity_df(self, gdf: GeoDataFrame):
        """
        Each entity process the input dataframe in different ways.
        Boundaries modify the entity_df by converting Polygons in Linestrings
        to (using the boundary method) and MultiLinestrings to LineStrings.
        A 'type' column is added if missing.
        """

        self._df = gdf
        self._df.reset_index(inplace=True, drop=True)


        geom_list = []
        # boundaries = df.boundary
        #
        # gdf = boundaries.explode(ignore_index=True)

        # The following is horrible and I hate it but for some reason the commented lines above
        # do not work for shapely 1.8 and geopandas 0.11 while they work perfectly with 2.0 and 0.13

        # This is to suppress the SettingWithCopyWarning (we are not working on a copy)
        pd.options.mode.chained_assignment = None

        for index, line in enumerate(self._df.loc[:, 'geometry']):
            if isinstance(line, Polygon):
                bound = line.boundary
                if isinstance(bound, MultiLineString):
                    for linestring in bound.geoms:
                        geom_list.append(linestring)
                else:
                    geom_list.append(bound)
            else:
                geom_list.append(line)

        for index, value in enumerate(geom_list):
            self._df.loc[index, 'geometry'] = value
        # When PZero moves to shapely 2.0 remove the lines between the comments
        # and uncomment the two lines above

        if 'type' not in self._df.columns:
            self._df['type'] = 'boundary'


class FractureNetwork(BaseEntity):
    """
    Fracture network base entity. Fracture networks are defined by one or
    more:

        + Fracture base entities

        + Boundary base entities

        + Nodes base entities

    All the data is represented in the entity_df and the different objects
    are defined by the 'type' column.

    FractureNetwork objects can be created in two ways depending on how
    the dataset is structured.

        1. If fractures and boundaries and nodes are saved in different shp files
        then use the add_fracture,add_boundary and add_nodes methods on an empty
        FractureNetwork object.

        2. If fractures and boundaries and nodes are saved in a single shp the
        geopandas dataframe can be directly fed when instantiating the class.
        In this case a type column must be set to indicate of which type the geometries are

    """

    def __init__(self, gdf: GeoDataFrame = None):

        self._fractures: Fractures = None
        self._boundaries: Boundary = None
        self._nodes: Nodes = None

        # Use the base entity init.
        super().__init__(gdf)

    @property
    def fractures(self) -> Fractures:
        """
        Retrieve the fracture objects

        :return: A fracture object
        """

        return self._fractures

    @fractures.setter
    def fractures(self, frac_obj: Fractures):
        """
        Set the fracture objects

        :param frac_obj:  Fracture object to be set
        """

        self._fractures = frac_obj

    @property
    def boundaries(self) -> Boundary:
        """
        Retrieve the Boundary object

        :return: The boundary object
        """

        return self._boundaries

    @boundaries.setter
    def boundaries(self, bound_obj: Boundary):
        """
        Set the boundary objects

        :param bound_obj: Boundary object
        """

        self._boundaries = bound_obj

    @property
    def nodes(self) -> Nodes:
        """
        Retrieve the nodes of the FractureNetwork

        :return: Nodes of the fracture network
        """

        return self._nodes

    @nodes.setter
    def nodes(self, nodes_obj: Nodes):
        """
        Set the nodes of the FractureNetwork

        :param nodes_obj: Nodes to be set
        """

        self._nodes = nodes_obj

    @property
    def entity_df(self) -> GeoDataFrame:
        """
        Each entity is based on a geopandas dataframe. This property returns or sets
        the entity_df of the given entity.

        :getter: Returns the GeoDataFrame
        :setter: Sets the GeoDataFrame
        :type: GeoDataFrame

        Notes
        -------
        When set the dataframe is modified to conform to the assigned entity structure.
        """

        fractures_df = self.fractures.entity_df
        boundaries_df = self.boundaries.entity_df

        if self.nodes is not None:
            nodes_df = self.nodes.entity_df
            df = pd.concat([nodes_df, fractures_df, boundaries_df], ignore_index=True)
        else:
            df = pd.concat([fractures_df, boundaries_df], ignore_index=True)

        df['id'] = df.index

        return df

    @entity_df.setter
    def entity_df(self, gdf: GeoDataFrame):
        """
        FractureNetworks modify the entity_df by extracting the different types
        (fractures, boundaries, nodes). After that, the appropriate base entities
        are created and set.

        Notes
        -----
        This is an internal method that is called when a df is set.

        """

        # self._df = gdf
        nodes = Nodes(gdf.loc[gdf['type'] == 'node'])
        fractures = Fractures(gdf.loc[gdf['type'] == 'fracture'])
        boundary = Boundary(gdf.loc[gdf['type'] == 'boundary'])

        self.nodes = nodes
        self.fractures = fractures
        self.boundaries = boundary

        # print(self.boundaries.entity_df)

    @property
    def vtk_object(self):
        df = self.entity_df
        vtk_obj = Rep.fracture_network_rep(df)
        return vtk_obj

    @vtk_object.setter
    def vtk_object(self, obj: DataSet):
        """
        FractureNetworks modify the vtkObject by extracting the different types
        (fractures, boundaries, nodes). After that, the appropriate vtkObject is
        set to the corresponding entity

        Notes
        -----
        This is an internal method that is called when a vtk is set.
        """

        frac_vtk = obj.extract_cells(obj.cell_data['type'] == 'fracture')
        bound_vtk = obj.extract_cells(obj.cell_data['type'] == 'boundary')
        node_vtk = obj.extract_points(obj.point_data['type'] == 'nodes', include_cells=False)

        self.fractures.vtk_object = frac_vtk
        self.boundaries.vtk_object = bound_vtk
        self.nodes.vtk_object = node_vtk

    def add_fractures(self, fractures: Fractures, name: str = None):

        """
        Method used to add fractures to the FractureNetwork

        :param fractures: Fracture object
        :param name: Name of the fractures added (for example set_1). By default is None
        """

        self.fractures = fractures

    def add_boundaries(self, boundaries: Boundary):
        """
        Method used to add boundaries to the FractureNetwork

        :param boundaries: Boundaries object
        """

        self.boundaries = boundaries

    def add_nodes(self, nodes: Nodes):
        """
        Method used to add nodes to the FractureNetwork

        :param nodes: Nodes object
        """

        # If the FractureNetwork df is empty use this as the start.
        # If not then append the Nodes base entity df information to the
        # existing df

        self.nodes = nodes
