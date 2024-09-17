import pytest
import logging
import pandas as pd
import matplotlib.colors as mcolors
import ezdxf
import os

from pandas.testing import assert_frame_equal
from geotechnics.drawings.borehole2D.borehole2D import *
from ezdxf.colors import int2rgb, aci2rgb

# Inputs and outputs data for this tests
@pytest.fixture(scope='session')
def reader():

    data = pd.read_excel(
        r'tests/drawings/data/t_boreholes_coords_outputs.xlsx'
    )
    
    return data


def get_dxf_data(dxf_file):
    """
    Retrieve information from dxf files and transform it into a dataframe
    
    :param dxf_file: File path.
    :type dxf_file: string
    
    :return: pandas DataFrame with all the entities data and other with all\
        the layers data.
    :rtype: pd.Dataframe, pd.Dataframe 
    """

    doc = ezdxf.readfile(dxf_file)
    msp = doc.modelspace()
    
    entities_list = []
    layers_list = []
    
    # Iterate over all entities in the Modelspace
    for entity in msp:
        
        # Get all attributes of the entity as a dictionary
        entity_attribs = entity.dxfattribs()
        
        entity_attribs['entity_type'] = entity.dxftype()
        
        # Getting vertices lists in entityes with it
        if entity.dxftype() == 'POLYLINE' or entity.dxftype() == 'LWPOLYLINE':
            entity_attribs['vertices'] = list(entity.vertices())
            
        elif entity.dxftype() == 'HATCH':
            for path in entity.paths.external_paths():
                entity_attribs['vertices'] = list(path.vertices)
               
        # Add the color to the dictionary
        color_index = entity.dxf.color
        if entity.has_dxf_attrib("true_color"):
            rgb = int2rgb(entity.dxf.true_color)
        else:
            if color_index == 256:
                rgb = "BY LAYER"
            else:
                rgb = aci2rgb(color_index)
        
        entity_attribs['color'] = rgb
        
        entities_list.append(entity_attribs)

    
    for layer in doc.layers:
            
        layer_attributes = layer.dxfattribs()
        
        # Add the color to the dictionary
        color_index = layer.color
        if layer.has_dxf_attrib("true_color"):
            rgb = int2rgb(layer.dxf.true_color)
        else:
            rgb = aci2rgb(color_index)
        
        layer_attributes['color'] = rgb
        
        layers_list.append(layer_attributes)

    # Create the DataFrames from the lists of dictionaries
    df_entities = pd.DataFrame(entities_list)
    df_layers = pd.DataFrame(layers_list)
    
    return df_entities, df_layers
    

def set_up_dxf(colors):
    """
    Creates a ezdxf doc and msp instance with the common layers
    :param colors: Dict with material names as keys and RGB colors as values
    :type colors: dict[str, (int, int, int)]
    
    :return: ezdxf doc and modelspace entities. 
    :rtype: ezdxf.new(), ezdxf.new().modelspace()
    """
    
    # Create a new DXF drawing
    doc = ezdxf.new()

    # Add new entities to the modelspace:
    msp = doc.modelspace()

    # Create a layer for each material
    for material in colors.keys():
        layer = doc.layers.add(material)
        layer.rgb = colors[material]
        
    # Create other necessary layers
    for layer, color in layers.items():
        layer = doc.layers.add(layer)
        layer.rgb = color
    
    return doc, msp
    
     
#------------------------------- evaluate_colors
@pytest.mark.parametrize("colors, df",[
    (
        {
            'clay 1': (255, 255, 255),
            'clay 2': "#000000",
            'sand 1':  "#F0F0F0"
        },
        pd.DataFrame(columns=['material'], data=['clay 1', 'clay 2', 'sand 1'])
    ),
    (
        {
            'clay 1': (255, 255, 255),
            'clay 2': "#000000",
        },
        pd.DataFrame(columns=['material'], data=['clay 1', 'clay 2'])
    )
])
def test_evaluate_colors_success(colors, df):
    
    colors_evaluation, colorslist = evaluate_colors(colors, df)
    
    rgb_colors = {}
    
    for material, color in colors.items():
        if type(color) == str:
            rgb_colors[material] = tuple(
                c * 255 for c in mcolors.to_rgb(colors[material])
            )
        else:
            rgb_colors[material] = color
    
    assert colors_evaluation == True
    assert colorslist == rgb_colors
    
    
@pytest.mark.parametrize("colors, df",[
    
    # Test non-hex string
    (
        {
            'clay 1': (255, 255, 255),
            'clay 2': "#000000",
            'sand 1':  "foo"
        },
        pd.DataFrame(columns=['material'], data=['clay 1', 'clay 2', 'sand 1'])
    ),
    # Test not valid rgb or rgba (wrong tuple size)
    (
        {
            'clay 1': (255, 255, 255, 400),
            'clay 2': "#000000",
        },
        pd.DataFrame(columns=['material'], data=['clay 1', 'clay 2'])
    ),
    # Test not valid rgb (wrong rgb number values)
    (
        {
            'clay 1': (300, 255, 255),
        },
        pd.DataFrame(columns=['material'], data=['clay 1'])
    ),
])
def test_evaluate_colors_failed_not_valid_color(colors, df, caplog):
    
    with caplog.at_level(logging.INFO):
        
        colors_evaluation, colorslist = evaluate_colors(colors, df)
        
    assert colors_evaluation == False
    assert colorslist == {}
    assert 'has a non-valid color.' in caplog.text


@pytest.mark.parametrize("colors, df",[
    (
        {
            'clay 1': (255, 255, 255),
            'clay 2': "#000000",
            'sand 1': "#000000"
        },
        pd.DataFrame(columns=['material'], data=['clay 1', 'clay 2', 'sand 1', 'sand 2'])
    )
])
def test_evaluate_colors_failed_no_color(colors, df, caplog):
    
    with caplog.at_level(logging.INFO):
        
        colors_evaluation, colorslist = evaluate_colors(colors, df)
        
    assert colors_evaluation == False
    assert colorslist == {}
    assert 'There is no color for ' in caplog.text


#------------------------------- get_colors
@pytest.mark.parametrize('colorscale', ['Pastel1', 'Pastel2', 'Accent'])
@pytest.mark.parametrize(
    'materials',
    [('clay'), ('clay', 'sand'), ('clay', 'sand', 'rock')]
)
def test_get_colors_success(colorscale, materials):
    
    colorsdict = get_colors(colorscale, materials)
    
    assert type(colorsdict) == dict
    assert all(material in colorsdict for material in materials)


@pytest.mark.parametrize(
    'materials',
    [('clay'), ('clay', 'sand'), ('clay', 'sand', 'rock')]
)
def test_get_colors_failed_colormap_name(materials, caplog):
    
    with caplog.at_level(logging.INFO):
        
        with pytest.raises(ValueError):
            
            colorsdict = get_colors('Wrong_colormap_name', materials)
            
            assert type(colorsdict) == dict
            assert 'Error creating the colors dict.' in caplog.text


#------------------------------- boreholes_coords
def test_boreholes_coords(reader): 
    
    input_columns = ['borehole_name', 'start', 'end', 'material']
    output_columns = ['x1', 'x2', 'y1', 'y2']
    comparison_output_columns = [f'{column}_output' for column in output_columns ]
    test_cases = reader[reader['test_function'] == 'test_boreholes_coords']
    
    groups = test_cases.groupby('scenario')
    
    for scenario, group in groups:
        
        df = group[input_columns].copy()
        borehole_thickness = group['borehole_thickness'].iloc[0]
        space_between_boreholes = group['space_between_boreholes'].iloc[0]
        elevation = bool(group['elevation'].iloc[0])
        draw_on_zero = bool(group['draw_on_zero'].iloc[0])
        
        function_output = boreholes_coords(df, borehole_thickness, space_between_boreholes, elevation, draw_on_zero)
        function_output = function_output[output_columns]
        
        comparison_output = group[comparison_output_columns]
        comparison_output.columns = output_columns
        
        try:
            assert_frame_equal(function_output, comparison_output, check_dtype=False)
            print(f'\nEvaluated scenario: {scenario}. It is ok!')
            assert True
        except AssertionError as e:
            print(f'\nError on scenario {scenario}')
            print(f'{e}')
            assert False


#------------------------------- draw_log
#------------------------------- draw_legend
#------------------------------- draw_dimension
#------------------------------- draw_borehole_name
"""
All the drawing functions have the same test structure:
- Create the drawing
- Save the drawing
- Read it again
- Read the reference drawing
- Create dataframes with the entities of both drawings
- Compare the dataframes

For this reason they are all covered in one test, parametrizes by 'function'

Pytest combined with assert_frame_equal outputs can identify pretty well the
tests cases when it failes.
"""
@pytest.mark.parametrize(
    'colors',
    [
        {
            'clay 1': (251, 180, 174),
            'clay 2': (204, 235, 197),
            'sand 1': (254, 217, 166),
            'sand 2': (229, 216, 189),
            'rock 1': (242, 242, 242),
        }
    ]
)
@pytest.mark.parametrize(
    'scenario',
    ['depth', 'elevation_elevation', 'elevation_zero']
)
@pytest.mark.parametrize('function', ['dimension', 'log', 'name', 'legend'])
def test_drawings(reader, colors, scenario, function):
    
    df = reader.rename(
        columns={
            'x1_output': 'x1',
            'x2_output': 'x2',
            'y1_output': 'y1',
            'y2_output': 'y2'
        }
    )
    df = df[df['scenario'] == scenario]
    
    doc, msp = set_up_dxf(colors)
    
    # Function test
    match function:
        case 'dimension':
            draw_dimension(df, msp)
        case 'log':
            draw_log(df, msp)
        case 'name':
            draw_borehole_name(df, msp)
        case 'legend':
            draw_legend(colors, msp)
    
    """
    ezdxf may lose or change some information when a file is saved. \
    Since we are comparing it with an existing file, \
    we will save and re-read the file to ensure both files have the same \
    structure.
    """
    
    provisory_file_path = 'test_log.dxf'
    doc.saveas(provisory_file_path)
    
    reference_file_path = f'tests/drawings/data/{function}_{scenario}.dxf'
    
    test_df, layers_test_df = get_dxf_data(provisory_file_path)
    reference_df, layers_reference_df = get_dxf_data(reference_file_path)
   
    # Assert all attributes but color
    try:
        assert_frame_equal(
            test_df,
            reference_df,
            check_dtype=False,
            check_index_type=False
        )
        assert True
    except AssertionError as e:
        print(f'{e}')
        assert False

    # Assert color
    """
    The color attribute for the hatchs is by layer (color=256).
    In order to assert their colors, compare the colors of their layers.
    """
    try:
        assert_frame_equal(
            layers_test_df,
            layers_reference_df,
            check_dtype=False,
            check_index_type=False
        )
        assert True
    except AssertionError as e:
        print(f'{e}')
        assert False
    
    if os.path.exists(provisory_file_path):
        os.remove(provisory_file_path)
