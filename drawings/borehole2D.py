import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors 

def get_colors(colorscale, n_colors):
    
    try:
        c_map = matplotlib.colormaps.get_cmap(colorscale)
        colors_array = np.linspace(0, 1, n_colors)
        colorlist = []
        
        for color in colors_array:
            rgba = c_map(color)
            hexacolor = matplotlib.colors.rgb2hex(rgba)
            colorlist.append(str(hexacolor))
            
    except:
        raise ValueError('')
    
    return colorlist


def borehole2D(
    df,
    path='',
    file_name='borehole2D.dxf',
    colors=None,
    colorscale=None,
    borehole_size=1,
    space_between_boreholes=5,
    legend = True,
    draw_name = True,
    elevation = False,
    draw_on_zero = True
    ):
    """
    Draw 2D boreholes in a dxf file.
    
    :param df: DataFrame of boreholes data where each row represents a material layer with the following boreholes parameters:
        - 'borehole_name' (str): Name of the borehole to which this layer belongs,
        - 'start' (int or float): Start depth or elevation of the layer. If using elevation, make sure to set elevation parameter to True,
        - 'end' (int or float): End depth or elevation of the layer. If using elevation, make sure to set elevation parameter to True,
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
    
    :param elevation: True when using elevation instead of borehole depth as input.
    :type elevation: bool
    
    :param draw_on_zero: When True the drawing will have the top of all boreholes set to y = 0 in CAD, instead of it's elevation.
    :type draw_on_zero: bool
    
    :return: dxf containing the drawing of the boreholes.
    :rtype: io.IOBase
     
    """
        
    # Evaluate columns
    required_columns = ['borehole_name', 'start', 'end', 'material']
    is_missing_columns = False if set(required_columns).issubset(df.columns) else True
    
    if is_missing_columns:
        raise ValueError('The dataframe do not has one of the following columns: borehole_name, start, end, material')
        
    # Evaluate data types
    df['eval_start'] = df['start'].apply(lambda x: isinstance(x, (int, float)))
    df['eval_end'] = df['end'].apply(lambda x: isinstance(x, (int, float)))

    # Transform non strings into strings in borehole_name and material columns
    df['borehole_name'] = df['borehole_name'].apply(lambda x: str(x))
    df['material'] = df['material'].apply(lambda x: str(x))
    
    # Exclude the lines where initial or final depth are not numbers
    value_error = df[(df['eval_start'] == False) | (df['eval_end'] == False)]
    value_error = value_error[required_columns]
    
    df = df[(df['eval_start'] == True) & (df['eval_end'] == True)]
    df = df[required_columns]
    
    # Sort df by the start of each layer of each borehole
    df = df.sort_values(by=['borehole_name', 'start'], ascending=[True, not elevation])
    
    # Evaluate colors for the materials
    number_of_materials = df['material'].nunique()
    
    # Generate colors for each material
    if colors == None or colorscale != None:
       evaluated_colors = get_colors('Pastel1', number_of_materials) if colorscale == None else get_colors(colorscale, number_of_materials)
       
    # Check if colors dict match all materials
    elif type(colors) == dict:
        
        materials_list = list(df['material'].unique())
        is_colors_ok = True
        
        # Evaluate if all materials have valid colors
        for material in materials_list:
            
            try:
                material_color = colors[material]
                is_valid_color = mcolors.is_color_like(colors[material])
                
                if not is_valid_color:
                    print(f'{material} has a non-valid color')
                    is_colors_ok = False
                    break
                    
            except:
                print(f'There is no color for {material}')
                is_colors_ok = False
                break
        
        evaluated_colors = get_colors(colorscale, number_of_materials) if is_colors_ok == False else colors
        
    else:
        raise ValueError('Colors parameter must be a dict')
        
    # Verify gaps and overlays in layers
    df['previous_layer_end'] = df['end'].shift(1, fill_value=df['start'].iloc[0])
    df['previous_borehole'] = df['borehole_name'].shift(1).bfill()
    
    df['is_gap_or_overlay'] = df['previous_layer_end'] != df['start']
    df['is_same_borehole'] = df['previous_borehole'] == df['borehole_name']
    
    gaps_and_overlays = df[df['is_gap_or_overlay'] & df['is_same_borehole']]
    
    
    
colors = {
    'clay 1': '#ffffff',
    'clay 2': '#ffffff',
    'sand 1': '#ffffff',
    'sand 2': '#ffffff',
    'rock 1': '#ffffff'
}

df = pd.read_excel('./tests/data/t_borehole2D.xlsx')
borehole2D(df, colors=colors, elevation=True)