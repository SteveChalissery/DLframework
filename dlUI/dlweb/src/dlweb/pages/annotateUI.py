# Importing all necessary Libraries

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, State, Output
import webbrowser

from ..app import app

# A Layout for annotations page
layout = html.Div([
    html.Div(id = 'annotate_div'),
    html.Div(id = 'hidden_div', style = {"display":"None"})
])

# Callbacks for annotation
@app.callback(
    Output('annotate_div', 'children'),
    Input('hidden_div', 'children')
)

def on_button_click(children):
    '''
    This function will redirects to cvat tool once you landed to home url of this site 
    Parameters:
        Input:
            None : None
        Output:
            CVAT tool : redirects to cvat tool once you landed to home url of this site.
    '''
    # A Function that redirects to CVAT tool when user opens the home page of this website
    return dcc.Location(href='http://20.81.152.2:8080/tasks', id="id123")

