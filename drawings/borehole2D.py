def get_colors(colorscale, n_colors):
    print('a')

def borehole2D(
    df,
    path='',
    file_name='borehole2D.dxf',
    colors=None,
    colorscale='None',
    borehole_size=1,
    space_between_boreholes=5,
    legend = True,
    draw_name = True
    ):
    """
    Draw 2D boreholes in a dxf file.
    
    :param df: DataFrame of boreholes data where each row represents a material layer with the following boreholes parameters:
        - 'borehole_name' (str): Name of the borehole to which this layer belongs,
        - 'initial_depth' (float): Initial depth or elevation of the layer,
        - 'final_depth' (float): Final depth or elevation of the layer,
        - 'material' (str): Material of the layer
    :type df: pandas.DataFrame
    
    :param path: Folder path where you want to store the output file.
    :type path: str
    
    :param file_name: Name of the output file. Must end with the extension ".dxf".
    :type file_name: str
    
    :param colors: Dict with material names as keys and colors as values. Colors can be specified in RGB or HEX.
    :type colors: dict
    
    :param colorscale: `Matplotlib qualitative colormap <https://matplotlib.org/stable/users/explain/colors/colormaps.html#colormaps>`_ \
        to be used in the creation of the drawing. If parameter colors is provided, coloscale will be ignored.
    :type colorscale: str
    
    :param borehole_size: Diameter of the borehole.
    :type borehole_size: float
    
    :param space_between_boreholes: Space given between each borehole in the drawing.
    :type space_between_boreholes: float
    
    :param legend: True for drawing the materials legend.
    :type legend: bool
    
    :param draw_name: True for drawing the borehole name above it.
    :type draw_name: bool
    
    :return: dxf containing the drawing of the boreholes.
    :rtype: io.IOBase
     
    """
    

