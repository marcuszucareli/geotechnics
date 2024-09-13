import pytest
import pandas as pd
import matplotlib.colors as mcolors

from geotechnics.drawings.borehole2D.borehole2D import evaluate_colors


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
