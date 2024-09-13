import pytest
import logging
import pandas as pd
import matplotlib.colors as mcolors

from pandas.testing import assert_frame_equal
from geotechnics.drawings.borehole2D.borehole2D import *

# Inputs and outputs data for this tests
@pytest.fixture(scope='session')
def reader():

    data = pd.read_excel(r'tests/drawings/data/t_boreholes_coords_outputs.xlsx')
    
    return data

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
            rgb_colors[material] = tuple(c * 255 for c in mcolors.to_rgb(colors[material]))
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
@pytest.mark.parametrize('materials', [('clay'), ('clay', 'sand'), ('clay', 'sand', 'rock')])
def test_get_colors_success(colorscale, materials):
    
    colorsdict = get_colors(colorscale, materials)
    
    assert type(colorsdict) == dict
    assert all(material in colorsdict for material in materials)

@pytest.mark.parametrize('materials', [('clay'), ('clay', 'sand'), ('clay', 'sand', 'rock')])
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
        
        
    
