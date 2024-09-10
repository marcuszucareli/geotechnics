import pandas as pd
import numpy as np
import matplotlib
import matplotlib.colors as mcolors
import logging
import ezdxf

# logging
logging.basicConfig(
    level=logging.INFO,  # Define o nível de log
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'  # Formato das mensagens
)

logger = logging.getLogger('borehole2D')

# List of layers to create
layers = {
    'legend_boxes': (255,255,255),
    'legend_text': (255,255,255),
    'depth_bar_box': (255,255,255),
    'depth_bar_text': (255,255,255),
    'borehole_name': (255,255,255),
    'borehole_boxes': (255,255,255)
}


# Evaluate colors sent by user, 
def evaluate_colors(colors, df):
    
    materials = list(df['material'].unique())
    colorlist = {}
    
    for material in materials:
        
        # Evaluate if this material has a color
        if material not in colors.keys():
            logger.info(f'There is no color for {material}. The dxf will be created with the program default colors.')
            return False, {}
        
        # Evaluate if it's a valid color
        if type(colors[material]) == tuple:
            color = tuple(c / 255 for c in colors[material])
        else:
            color = mcolors.to_rgb(colors[material])
        
        is_valid_color = mcolors.is_color_like(color)
        
        if not is_valid_color:
            logger.info(f'{material} has a non-valid color. The dxf will be created with the program default colors.')
            return False, {}
        else:
            rgb = tuple(int(x * 255) for x in color)
            colorlist[material] = rgb
            
    return True, colorlist
    

# Get a list with n_colors of a coloscale
def get_colors(colorscale, materials):
    
    try:
        
        colorlist = {}
        c_map = matplotlib.colormaps.get_cmap(colorscale)
        colors_array = np.linspace(0, 1, len(materials))
        
        i = 0
        for color in colors_array:
            
            rgba = c_map(color)
            rgb = mcolors.to_rgb(rgba)
            rgb = tuple(int(x * 255) for x in rgb)
            
            colorlist[materials[i]] = rgb
            
            i += 1
                        
    except:
        raise ValueError('Error creating the colors dict')
    
    return colorlist


# Draw logs
def draw_log(df, msp):
    
    # Draw the hatch's
    for row in df.iterrows():
        
        # Get the coordinate of the layer
        y_1 = row[1].y1
        y_2 = row[1].y2
        x_1 = row[1].x1
        x_2 = row[1].x2

        # Get the material name
        material = row[1].material

        # Create hatch entity first, so it will be showed back of the lines // Color 256 = By Layer
        hatch = msp.add_hatch(color=256, dxfattribs={'layer': material})

        # Draw the square using polyline in the given layer
        points = [(x_1, -y_1), (x_2, -y_1), (x_2, -y_2), (x_1, -y_2)]
        
        # Create the Polyline to further association
        lwpolyline = msp.add_lwpolyline(points, format="xyb", close=True,  dxfattribs={'layer': 'borehole_boxes'})

        # Polyline path for hatch create the draw
        path = hatch.paths.add_polyline_path(
            
            # get path vertices from associated LWPOLYLINE entity
            lwpolyline.get_points(format="xyb"),
            
            # get closed state also from associated LWPOLYLINE entity
            is_closed=lwpolyline.closed,
        )
        # Set association between boundary path and LWPOLYLINE
        hatch.associate(path, [lwpolyline])

# Calculate the coordinates of the boreholes boxes for each layer
def boreholes_coords(df, borehole_thickness, space_between_boreholes, elevation, draw_on_zero):

    df['multiplier'] = pd.Categorical(df['borehole_name']).codes
    df['x1'] = (borehole_thickness + space_between_boreholes) * df['multiplier']
    df['x2'] = borehole_thickness + df['x1']
    df['borehole_start'] = df.groupby('borehole_name')['start'].transform('first')
    
    match [elevation, draw_on_zero]:
        
        case [True, True]:
            df['y1'] = df['start'] - df['borehole_start']
            df['y2'] = df['end'] - df['borehole_start']
        
        case [True, False]:
            df['y1'] = df['start']
            df['y2'] = df['end']
        
        case _:
            df['y1'] = -df['start']
            df['y2'] = -df['end']
    
    return df


def borehole2D(
    df,
    path='',
    file_name='borehole2D.dxf',
    colors=None,
    colorscale='Pastel1',
    borehole_thickness=1,
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
        - 'start' (int or float): Start depth or elevation of the layer. If using elevation, make sure to set elevation parameter to True,\
            also when selecting depth, it is assumed that the initial value is zero and it will increase positively with the depth of the borehole.
        - 'end' (int or float): End depth or elevation of the layer. If using elevation, make sure to set elevation parameter to True,\
            also when selecting depth, it is assumed that the initial value is zero and it will increase positively with the depth of the borehole.
        - 'material' (str): Material of the layer
    :type df: pd.DataFrame
    
    :param path: Folder path where you want to store the output file.
    :type path: str
    
    :param file_name: Name of the output file. Must end with the extension ".dxf".
    :type file_name: str
    
    :param colors: Dict with material names as keys and colors as values. Colors can be specified as RGB tuples (255,255,255) or HEX (#ffffff).
    :type colors: dict[str, Any]
    
    :param colorscale: `Matplotlib qualitative colormap <https://matplotlib.org/stable/users/explain/colors/colormaps.html#colormaps>`_ \
        to be used in the creation of the drawing. If parameter colors is provided, coloscale will be ignored.
    :type colorscale: str
    
    :param borehole_thickness: Diameter of the borehole.
    :type borehole_thickness: float
    
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
    
    logger.info(f'Number of layers with value error: {len(value_error)}')
    
    df = df[(df['eval_start'] == True) & (df['eval_end'] == True)]
    df = df[required_columns]
    
    # Sort df by the start of each layer of each borehole
    df = df.sort_values(by=['borehole_name', 'start'], ascending=[True, not elevation])
    
    # Evaluate colors if it's user's inputs
    if type(colors) == dict:
        colors_evaluation, colorslist = evaluate_colors(colors, df)
    else:
        colors_evaluation = False
    
    # Define colors if not evaluated before
    if colors_evaluation:
        evaluated_colors = colorslist
    else:
        evaluated_colors = get_colors(colorscale, df['material'].unique())
        
    # Verify gaps and overlays in layers
    df['previous_layer_end'] = df['end'].shift(1, fill_value=df['start'].iloc[0])
    df['previous_borehole'] = df['borehole_name'].shift(1).bfill()
    
    df['is_gap_or_overlay'] = df['previous_layer_end'] != df['start']
    df['is_same_borehole'] = df['previous_borehole'] == df['borehole_name']
    
    gaps_and_overlays = df[df['is_gap_or_overlay'] & df['is_same_borehole']]
    logger.info(f'Number of layers with gaps or overlays: {len(gaps_and_overlays)}')
    
    # Calculate boreholes points coordinates for each layer
    df = boreholes_coords(df, borehole_thickness, space_between_boreholes, elevation, draw_on_zero)
    
    # Create a new DXF drawing
    doc = ezdxf.new()

    # Add new entities to the modelspace:
    msp = doc.modelspace()

    print(evaluated_colors)
    i = 0
    # Create a layer for each material
    for material in pd.unique(df['material']):
        layer = doc.layers.add(material)
        layer.rgb = evaluated_colors[material]
        
        i += 1
        
    # Create other necessary layers
    for layer, color in layers.items():
        layer = doc.layers.add(layer)
        layer.rgb = color
        
        i += 1
    
    # Draw the associative hatchs and boxes of the logs
    draw_log(df, msp)
    
    doc.saveas("borehole_logs.dxf")
    
    
colors = {
    'clay 1': '#ffffff',
    'clay 2': '#ffffff',
    'sand 1': '#ffffff',
    'sand 2': '#f0f0f0',
    # 'rock 1': (0, 0, 0)
}

df = pd.read_excel('./tests/data/t_borehole2D.xlsx')
borehole2D(df, colors=colors)