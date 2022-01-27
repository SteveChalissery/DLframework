# importing all the necessary libraries
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, State, Output
import requests
import json
from flask import request
import os
from PIL import Image

from ..app import app


images_div = []

# Layout for teststatus page
layout = html.Div([
    dcc.Location(id="url", refresh=False),

    html.Br(),

    # Creating a teststatus button
    dbc.Button('testStatus', id = "teststatus", color = "primary", className = "mr-1"),
    html.Div(id = 'teststatus_div', style = {
        "display" : "flex"
    }),

    html.Br(),
    html.Br(),

    # Creating a deployment button
    dbc.Button('Deployment', id = "deployment", color = "primary", className = "mr-1"),
    html.Div(id = 'deployment_div'),

    html.Br(),
    html.Br(),
    
])


# Callback for getting teststatus
@app.callback(
    Output('teststatus_div', 'children'),
    [
        Input('teststatus', 'n_clicks')
	],
    State("url", "search")
)

def testStatus(n, search):
    ''' 
    This function will return status of testing
    Parameters:
        Input:
            url : Takes the url which contains uniqueid and modelname
        Output:
            status : status of testing
    '''
    test_status = ""
    
    # Extracting uniqueid from url search
    uniqueid = search.split('?')[1].split('&')[0].split('=')[1]

    # Extracting modelname from urlsearch
    modelname = search.split('&')[1].split('@')[0].split('=')[1].strip('[%27').strip('27%]')
    res_dict = {}
    models = []
    models.append(modelname)
    res_dict['model_name'] = modelname
    res_json = MakeJson(res_dict)
    layout = ""

    if n:
        url = 'https://dltesting.azurewebsites.net/testStatus/' + str(uniqueid)
        status = requests.get(url, json = res_json)
        test_status = status.text
        images = []
        # Checking whether the testing of atleast one image is completed or not
        if 'box' in test_status:
            test_status_json = {}
            for key, value in status.json().items():
                if type(value) is dict:
                    test_status_json.update(value)
                    for k, v in test_status_json.items():
                        images.append(v['infered_img'])
            images_div = []
            n = None
            # Creating and appending layout to a list for each and every image
            for image in images:
                # Creating layout for every image
                layout = html.Div([
                    html.A([
                        html.Img(src = image, style = {
                        'height' : "300px",
                        'width' : "300px"
                        }),
                    ], href = image),
                    html.Br(),
                    html.Br(),
                    html.Br(),
                ])
                images_div.append(layout)
            return images_div
        else:
            return test_status


# Callback for redirecting to deployment page
@app.callback(
    Output('deployment_div', 'children'),
    [
        Input('deployment', 'n_clicks')
	],
    State("url", "search")
)


def deploy_page(deploy_n, search):
    '''
    This function will redirects to testing page
    Parameters:
        Input:
            url : button click and url with uniqueid
        Output:
            New tab : redirects to deploy page
    '''
    if deploy_n:
        uniqueid = search.split('?')[1].split('&')[0].split('=')[1]
        annotate_name = search.split('@')[1].split('=')[1]

        # Generating URL for the testing UI with uniqueid
        pathname = f"/deploy?uuid={uniqueid}&name={annotate_name}"
        return dcc.Location(href = pathname, id = "deployid")


def MakeJson(res_dict):
    '''
    This function will return the json file 
    Parameters:
        Input:
            dictionary : dictionary with all user inputs
        Output:
            config : resultant Inputs in JSON format which will be given as input to request.
    '''
    load_json = json.dumps(res_dict, indent=4)
    res_json = json.loads(load_json)
    return res_json
