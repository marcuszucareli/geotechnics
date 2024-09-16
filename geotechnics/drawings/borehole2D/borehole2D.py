import pandas as pd
import numpy as np
import matplotlib
import matplotlib.colors as mcolors
import logging
import ezdxf

from ezdxf.enums import TextEntityAlignment

# logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('borehole2D')

# Dict of layers and their colors used in the drawing
layers = {
    'legend_boxes': (255,255,255),
    'legend_text': (255,255,255),
    'dimension_text': (255,255,255),
    'borehole_boxes': (255,255,255),
    'borehole_text': (255,255,255),
}


def evaluate_colors(colors, df):
    """
    Evaluate colors sent by user
    
    :param colors: The colors dict with materials as keys and colors as values (RGB, HEX)
    :type colors: dict
    
    :param df: DataFrame of boreholes data where each row represents a material layer.
    :type df: pd.DataFrame
    
    :return: True if the colors match the requirements for all materials and the dict with the colors in rgb tuples.
    :rtype: tuple(bool, dict)
    """
    
    materials = list(df['material'].unique())
    colorsdict = {}

    for material in materials:
        
        # Evaluate if this material has a color
        if material not in colors.keys():
            logger.info(f'There is no color for {material}. The dxf will be created with the program default colors.')
            return False, {}
        
        try:
            # Evaluate if it's a valid color
            if type(colors[material]) == tuple:
                color = tuple(c / 255 for c in colors[material])    # If it's RGB
            else:
                color = mcolors.to_rgb(colors[material])            # If it's HEX
        
            is_valid_color = mcolors.is_color_like(color)
        except:
            is_valid_color = False

        if not is_valid_color:
            logger.info(f'{material} has a non-valid color. The dxf will be created with the program default colors.')
            return False, {}
        else:
            rgb = tuple(int(x * 255) for x in color)
            colorsdict[material] = rgb
            
    return True, colorsdict
    

def get_colors(colorscale, materials):
    """
    Create the colors dict to be used in the drawing when they are not provided.
    
    :param colorscale: The colorscale to be used to create the colorslist.
    :type colorscale: str
    
    :param materials: List with the names of the materials.
    :type materials: list[str]
    
    :return: The dict with the materials as keys and their colors in rgb tuples as values.
    :rtype: dict
    """
    
    try:
        
        colorsdict = {}
        c_map = matplotlib.colormaps.get_cmap(colorscale)
        colors_array = np.linspace(0, 1, len(materials))
        
        i = 0
        for color in colors_array:
            
            rgba = c_map(color)
            rgb = mcolors.to_rgb(rgba)
            rgb = tuple(int(x * 255) for x in rgb)
            
            colorsdict[materials[i]] = rgb
            
            i += 1
                        
    except:
        raise ValueError(f'Error creating the colors dict. Verify the colorscale name you provided: {colorscale}')
    
    return colorsdict


def boreholes_coords(df, borehole_thickness, space_between_boreholes, elevation, draw_on_zero):
    """
    Create the coordinates needed to draw the boxes and hatches of the layers.
    
    :param df: DataFrame of boreholes data where each row represents a material layer with the following boreholes parameters:
        - 'borehole_name' (str): Name of the borehole to which this layer belongs,
        - 'start' (int or float): Start depth or elevation of the layer. If using elevation, make sure to set elevation parameter to True,\
            also when selecting depth, it is assumed that the initial value is zero and it will increase positively with the depth of the borehole.
        - 'end' (int or float): End depth or elevation of the layer. If using elevation, make sure to set elevation parameter to True,\
            also when selecting depth, it is assumed that the initial value is zero and it will increase positively with the depth of the borehole.
        - 'material' (str): Material of the layer
    :type df: pd.DataFrame
       
    :param borehole_thickness: Diameter of the borehole.
    :type borehole_thickness: float
    
    :param space_between_boreholes: Space given between each borehole in the drawing.
    :type space_between_boreholes: float
    
    :param elevation: True when using elevation instead of borehole depth as input.
    :type elevation: bool
    
    :param draw_on_zero: When True the drawing will have the top of all boreholes set to y = 0 in CAD, instead of it's elevation.
    :type draw_on_zero: bool
    
    :return: df containing the coordinates needed to draw the boxes and hatches of the layers.
    :rtype: pd.DataFrame
     
    """
    
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


def draw_log(df, msp):
    """
    Draw the logs boxes as polylines and hatches
    
    :param df: The dataframe with the material and box coordinates of each layer of each borehole. 
    :type df: pd.Dataframe
    
    :param msp: ezdxf modelspace entity where the drawing will be created
    :type msp: ezdxf.new().modelspace()
    
    :return: None
    :rtype: None
    """
    
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
        points = [(x_1, y_1), (x_2, y_1), (x_2, y_2), (x_1, y_2)]
        
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


def draw_legend(colors, msp):
    """
    Draw the legend in the drawing
    
    :param colors: Dict with material names as keys and RGB colors as values
    :type colors: dict[str, (int, int, int)]
    
    :param msp: ezdxf modelspace entity where the drawing will be created
    :type msp: ezdxf.new().modelspace()
    
    :return: None
    :rtype: None
    """
    
    multiplier = 0
    
    box_heigth = 1
    distance_between_boxes = .5
    
    # Draw legend
    for material, color in colors.items():

        
        
        # Calculate the initial y1 coordinate
        y_1 = - box_heigth - multiplier * (box_heigth + distance_between_boxes)
        
        # Calculate the x1 coordinate of the material
        x_1 = -20

        # Define the 4 polyline points of the box and the text start
        p1 = (x_1, y_1)
        p2 = (x_1, y_1 + box_heigth)
        p3 = (x_1 + 1.618, y_1 + box_heigth)
        p4 = (x_1 + 1.618, y_1)
        p5 = (x_1 + 1.618 + 1, y_1)

        # Create hatch entity first, so it will be showed back of the lines // Color 256 = By Layer
        hatch = msp.add_hatch(color=256, dxfattribs={'layer': material})

        # Draw the squares using polyline in the given layer
        points = [p1, p2, p3, p4, p1]
        
        # Create the Polyline to further association
        lwpolyline = msp.add_lwpolyline(points, format="xyb", close=True,  dxfattribs={'layer': 'legend_boxes'})

        # Polyline path for hatch create the draw
        path = hatch.paths.add_polyline_path(
            # get path vertices from associated LWPOLYLINE entity
            lwpolyline.get_points(format="xyb"),
            # get closed state also from associated LWPOLYLINE entity
            is_closed=lwpolyline.closed,
        )
        # Set association between boundary path and LWPOLYLINE
        hatch.associate(path, [lwpolyline])

        # Write the name of the material
        msp.add_text(
            material,
            dxfattribs={
                'height': 1,
                'layer': 'legend_text',
            }
        ).set_placement(p5, align=TextEntityAlignment.LEFT)
        
        multiplier += 1


def draw_dimension(df, msp):
    """
    Draw the legend in the drawing
    
    :param df: The dataframe with the material and box coordinates of each layer of each borehole. 
    :type df: pd.Dataframe
    
    :param msp: ezdxf modelspace entity where the drawing will be created
    :type msp: ezdxf.new().modelspace()
    
    :return: None
    :rtype: None
    """
    
    drew_layers = []

    for row in df.iterrows():
        
        x_start = row[1].x1 - .5
        y_start = row[1].y1
        dimension_start = str(round(row[1].start, 2))
        
        x_end = row[1].x1 - .5
        y_end = row[1].y2
        dimension_end = str(round(row[1].end, 2))
        
        start_dimension_info = ((x_start, y_start), dimension_start)
        end_dimension_info = ((x_end, y_end), dimension_end)
        
        dimensions_to_draw = [start_dimension_info, end_dimension_info]
        
        for dimension in dimensions_to_draw:
            
            is_drew = dimension in drew_layers
            
            if not is_drew:
                
                # Write the dimension
                msp.add_text(
                    dimension[1],
                    dxfattribs={
                        'height': .5,
                        'layer': 'dimension_text',
                    }
                ).set_placement(dimension[0], align=TextEntityAlignment.MIDDLE_RIGHT)
                
                drew_layers.append(dimension)


def draw_borehole_name(df, msp):
    """
    Draw the legend in the drawing
    
    :param df: The dataframe with the material and box coordinates of each layer of each borehole. 
    :type df: pd.Dataframe
    
    :param msp: ezdxf modelspace entity where the drawing will be created
    :type msp: ezdxf.new().modelspace()
    
    :return: None
    :rtype: None
    """
    
    boreholes = df.groupby('borehole_name').first()
    
    for borehole in boreholes.iterrows():
        
        x = (borehole[1].x1 + borehole[1].x2) / 2
        y = max(borehole[1].y1, borehole[1].y2) + 2
        
        # Write borehole name
        msp.add_text(
            borehole[0],
            dxfattribs={
                'height': .5,
                'layer': 'borehole_text',
            }
        ).set_placement((x,y), align=TextEntityAlignment.CENTER)


def borehole2D(
    df,
    elevation = False,
    borehole_thickness=1,
    space_between_boreholes=5,
    legend = True,
    borehole_name = True,
    dimension = True,
    draw_on_zero = True,
    colors=None,
    colorscale='Pastel1',
    path='borehole2D.dxf',
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
    
    :param path: Path to store the output file. Must end with the extension ".dxf"
    :type path: str
    
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
    
    :param borehole_name: True for drawing the borehole name above it.
    :type borehole_name: bool
    
    :param dimension: True for writing the depth or elevation of each layer.
    :type dimension: bool
    
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
    df['material'] = df['material'].fillna('unspecified soil')
    
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

    # Create a layer for each material
    for material in pd.unique(df['material']):
        layer = doc.layers.add(material)
        layer.rgb = evaluated_colors[material]
        
    # Create other necessary layers
    for layer, color in layers.items():
        layer = doc.layers.add(layer)
        layer.rgb = color
    
    # Draw the associative hatches and boxes of the logs
    draw_log(df, msp)
    
    # Draw legend
    if legend:
        draw_legend(evaluated_colors, msp)
        
    # Draw dimension
    if dimension:
        draw_dimension(df, msp)
    
    # Draw borehole name
    if borehole_name:
        draw_borehole_name(df, msp)
    
    try:
        doc.saveas(path)
    except:
        raise ValueError(f'Error saving the drawing. Verify the path parameter.')
