"""
FracAbility has different types of data that needs to be represented in different ways. In the Plotters module
different class adapters are proposed to plot the data. It is possible to plot:


Fracture Network (entity):


1. The geopandas dataframe -> matplotlib:
    + Fractures:
        + Rose plot
        + Backbone(s) -> Different colors if multiple backbones are present
    + Boundary
    + Nodes:
        + Different colors and shapes depending on the node type

2. The VTK entities -> pyvista:
    + Fractures:
        + Backbone(s) -> Different colors if multiple backbones are present
    + Boundary
    + Nodes:
        + Different colors depending on the node type

3. The topology data -> matplotlib:
    + I,Y,X node proportions in a ternary plot

Fracture network (statistics):

1. The statistics -> matplotlib:

    + Single distribution plot (each alone or together):
        + pdf
        + cdf
        + sf
        + summary table

    + Multiple distribution plot:
        + cdf vs ecdf
        + pdf vs histograms
        + P-P and Q-Q plot?

"""

import matplotlib.pyplot as plt
import seaborn as sns
from pyvista import Plotter
import ternary
from fracability.operations.Statistics import NetworkDistribution
import numpy as np


def matplot_nodes(entity, markersize=5, return_ax=False):

    if 'Fracture net plot' not in plt.get_figlabels():
        figure = plt.figure(num=f'Fractures plot')

        ax = plt.subplot(111)
    else:
        ax = plt.gca()

    points = entity.vtk_object.points
    node_types = entity.vtk_object['node_type']
    I = np.where(node_types == 1)
    Y = np.where(node_types == 3)
    X = np.where(node_types == 4)
    U = np.where(node_types == 5)

    ax.plot(points[I][:, 0], points[I][:, 1], 'or', markersize=markersize)
    ax.plot(points[Y][:, 0], points[Y][:, 1], '^g', markersize=markersize)
    ax.plot(points[X][:, 0], points[X][:, 1], 'sb', markersize=markersize)
    ax.plot(points[U][:, 0], points[U][:, 1], 'py', markersize=markersize)

    if return_ax:
        return ax
    else:
        plt.show()


def matplot_frac_bound(entity, linewidth=2, color='black', return_ax=False):

    if 'Fracture net plot' not in plt.get_figlabels():
        figure = plt.figure(num=f'Fractures plot')

        ax = plt.subplot(111)
    else:
        ax = plt.gca()

    entity.entity_df.plot(ax=ax, color=color, linewidth=linewidth)

    if return_ax:
        return ax
    else:
        plt.show()


def matplot_frac_net(entity, markersize=5, linewidth=2, color=['black', 'blue'], return_ax=False):

    figure = plt.figure(num=f'Fracture net plot')
    ax = plt.subplot(111)
    nodes = entity.nodes
    fractures = entity.fractures
    boundary = entity.boundaries

    if fractures is not None:
        matplot_frac_bound(fractures, color=color[0], return_ax=True)
    if boundary is not None:
        matplot_frac_bound(boundary, color=color[1], return_ax=True)
    if nodes is not None:
        matplot_nodes(nodes, return_ax=True)

    if return_ax:
        return ax
    else:
        plt.show()


def vtkplot_nodes(entity, markersize=7, return_plot= False):

    plotter = Plotter()

    class_dict = {
        1: 'I',
        2: 'V',
        3: 'Y',
        4: 'X',
        5: 'U',
        6: 'Y2'
    }
    cmap_dict = {
        'I': 'Blue',
        'Y': 'Green',
        'Y2': 'Cyan',
        'X': 'Red',
        'U': 'Yellow'
    }

    nodes = entity.vtk_object

    class_names = [class_dict[i] for i in nodes['node_type']]

    used_tags = list(set(class_names))
    used_tags.sort()
    cmap = [cmap_dict[i] for i in used_tags]

    sargs = dict(interactive=False,
                 vertical=False,
                 height=0.1,
                 title_font_size=16,
                 label_font_size=14)

    actor = plotter.add_mesh(nodes,
                             scalars=class_names,
                             render_points_as_spheres=True,
                             point_size=markersize,
                             show_scalar_bar=True,
                             scalar_bar_args=sargs,
                             cmap=cmap)

    if return_plot:
        return actor
    else:
        plotter.show()


def vtkplot_fractures(entity, linewidth=1, color='white', color_set=False, return_plot=False):
    plotter = Plotter()

    vtk_object = entity.vtk_object
    if color_set:
        if 'set' in vtk_object.array_names:
            actor = plotter.add_mesh(entity.vtk_object,
                                     scalars='set',
                                     line_width=linewidth,
                                     cmap=['Red','Blue'],
                                     show_scalar_bar=False)
        else:
            actor = plotter.add_mesh(entity.vtk_object,
                                     color=color,
                                     line_width=linewidth,
                                     show_scalar_bar=False)
    else:

        actor = plotter.add_mesh(entity.vtk_object,
                         color=color,
                         line_width=linewidth,
                         show_scalar_bar=False)

    if return_plot:
        return actor
    else:
        plotter.show()


def vtkplot_boundaries(entity, linewidth=1, color='white', return_plot=False):
    plotter = Plotter()

    actor = plotter.add_mesh(entity.vtk_object,
                     color=color,
                     line_width=linewidth,
                     show_scalar_bar=False)

    if return_plot:
        return actor
    else:
        plotter.show()


def vtkplot_frac_net(entity, markersize=5, linewidth=2, color=['white', 'white'], return_plot=False):

    plotter = Plotter()

    fractures = entity.fractures
    nodes = entity.nodes
    boundaries = entity.boundaries


    if nodes is not None:
        node_actor = vtkplot_nodes(nodes, return_plot=True)
        plotter.add_actor(node_actor)
    if fractures is not None:
        fractures_actor = vtkplot_fractures(fractures, color=color[0], return_plot=True)
        plotter.add_actor(fractures_actor)
    if boundaries is not None:
        boundary_actor = vtkplot_boundaries(boundaries, color=color[1], return_plot=True)
        plotter.add_actor(boundary_actor)

    if return_plot:
        actors = plotter.actors()
        return actors
    else:
        plotter.show()


def matplot_stats_summary(network_distribution: NetworkDistribution, function_list: list = ['pdf', 'cdf', 'sf']):
    sns.set_theme()
    """
    Summarize PDF, CDF and SF functions and display mean, std, var, median, mode, 5th and 95th percentile all
    in a single plot.
    A range of values and the resolution can be defined with the x_min, x_max and res parameters.

    Parameters
    -------
    x_min: Lower value of the range. By default is set to 0

    x_max: Higher value of the range. If None the maximum length of the dataset is used. None by default

    res: Point resolution between x_min and x_max. By default is set to 1000

    """

    cdf = network_distribution.ecdf.cdf
    x_vals = cdf.quantiles

    distribution = network_distribution.distribution
    name = network_distribution.distribution_name

    original_data = network_distribution.fit_data

    fig = plt.figure(num=f'{name} summary plot', figsize=(13, 7))
    fig.text(0.5, 0.02, 'Length [m]', ha='center')
    fig.text(0.5, 0.95, name, ha='center')
    fig.text(0.04, 0.5, 'Density', va='center', rotation='vertical')

    for i, func_name in enumerate(function_list[:3]):
        func = getattr(distribution, func_name)

        y_vals = func(x_vals)

        plt.subplot(2, 2, i+1)

        sns.lineplot(x=x_vals, y=y_vals, color='r', label=f'{name} {func_name}')

        if func_name == 'pdf':
            sns.histplot(original_data.lengths, stat='density', bins=50)
        if func_name == 'cdf':
            sns.lineplot(x=x_vals, y=cdf.probabilities, color='b', label='Empirical CDF')

        plt.title(func_name)
        plt.grid(True)
        plt.legend()

    plt.subplot(2, 2, i+2)
    plt.axis("off")
    plt.ylim([0, 8])
    plt.xlim([0, 10])
    dec = 4

    text_mean = f'Mean = {np.round(network_distribution.mean, dec)}'
    text_std = f'Std = {np.round(network_distribution.std, dec)}'
    text_var = f'Var = {np.round(network_distribution.var, dec)}'
    text_median = f'Median = {np.round(network_distribution.median, dec)}'
    text_mode = f'Mode = {np.round(network_distribution.mode, dec)}'
    text_b5 = f'5th Percentile = {np.round(network_distribution.b5, dec)}'
    text_b95 = f'95th Percentile = {np.round(network_distribution.b95, dec)}'

    plt.text(0, 7.5, 'Summary table')
    plt.text(0, 6.5, text_mean)
    plt.text(0, 5.5, text_median)
    plt.text(0, 4.5, text_mode)
    plt.text(0, 3.5, text_b5)
    plt.text(0, 2.5, text_b95)
    plt.text(0, 1.5, text_std)
    plt.text(0, 0.5, text_var)

    plt.text(6, 7.5, 'Test results:')

    text_crit_val = f'BIC value = {np.round(network_distribution.BIC, 3)}'
    text_result = f'AICc value = {np.round(network_distribution.AICc, 3)}'
    text_ks_val = f'Log Likelihood value = {np.round(network_distribution.log_likelihood, 3)}'

    plt.text(6, 6.5, text_result)
    plt.text(6, 5.5, text_crit_val)
    plt.text(6, 4.5, text_ks_val)

    plt.show()


def matplot_ternary(entity, merge_set_intersection=True):

    """
    Plot the ternary diagram for nodes
    :param entity: 
    :return: 
    """
    figure, tax = ternary.figure(scale=100)
    figure.set_size_inches(10, 10)

    if entity.name == 'FractureNetwork':
        nodes = entity.nodes
    elif entity.name == 'Nodes':
        nodes = entity

    PI, PY, PX = nodes.node_count[: 3]
    points = [(PX, PI, PY)]

    tax.scatter(points, marker='o', color='red', label='Classification')

    for n in range(8):
        n += 1
        A1 = np.array([[1, 1, 1], [0, 0, 1], [-n, 4, 0]])
        B = np.array([1, 0, 4 - n])

        X1 = np.linalg.inv(A1).dot(B) * 100
        if n < 4:
            side = [1, 0, 0]
        else:
            side = [0, 1, 0]
        A2 = np.array([[1, 1, 1], side, [-n, 4, 0]])

        X2 = np.linalg.inv(A2).dot(B) * 100

        tax.line(X1, X2, color='black', linewidth=1, alpha=n / 8)

    ax = tax.get_axes()
    ax.text(76.8, 21.3, 8)
    ax.text(74.8, 23.8, 7)
    ax.text(73.5, 27.9, 6)
    ax.text(71, 32.3, 5)
    ax.text(69.1, 38, 4)
    ax.text(65.8, 45, 3)
    ax.text(62.7, 54, 2)
    ax.text(57, 66.5, 1)

    tax.right_corner_label("X", fontsize=15)
    tax.top_corner_label("I", fontsize=15)
    tax.left_corner_label("Y", fontsize=15)

    tax.get_axes().set_aspect(1)  # This is used to avoid deformation when rescaling the plotter window
    # tax.clear_matplotlib_ticks()
    tax.get_axes().axis('off')

    plt.show()


