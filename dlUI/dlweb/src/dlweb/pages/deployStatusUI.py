# importing all the necessary libraries
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, State, Output
import requests
import json
from flask import request
import os
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import subprocess

connect_str = "DefaultEndpointsProtocol=https;AccountName=stdliopplatformdev001;AccountKey=Svo4kbk1P5GD4ES0IgWX4olyJq4MA75EEnz+QlPAaBFJOUk0RzblXKCEBgo3q5LeQktjg5Gw5lYP/2rSxiBcSA==;EndpointSuffix=core.windows.net"

from ..app import app

# Layout for teststatus page
layout = html.Div([
    dcc.Location(id="url", refresh=False),

    html.Br(),

    # Creating a teststatus button
    dbc.Button('deployStatus', id = "deploystatus", color = "primary", className = "mr-1"),
    html.Div(id = 'deploystatus_div', style = {
        "display" : "flex"
    }),

    html.Br(),
    html.Br(),

    # Creating a div for nodered button
    html.Div(id = 'nodered_div'),
	
    # Creating div for modelname for autoannotation
    html.Div(id = 'automodel_div'),

    # Creating deploy button
    dbc.Button(children = 'DLService', id = "dlservice", color = "primary", className = "mr-1", n_clicks = 0),
    html.Div(id = "dlservice_div"),

    html.Br(),
    html.Br(),
    
])

@app.callback(
    Output('nodered_div', 'children'),
    [
        Input('node_red_button', 'n_clicks')
	]
)

def nodered_page(nodered_n):
    '''
    This function will redirects to testing page
    Parameters:
        Input:
            url : button click and url with uniqueid
        Output:
            New tab : redirects to deploy page
    '''
    if nodered_n:

        # Generating URL for the testing UI with uniqueid
        pathname = f"https://noderedserver.azurewebsites.net"
        return dcc.Location(href = pathname, id = "node_red_id")


# Callback for getting deploystatus
@app.callback(
    Output('deploystatus_div', 'children'),
    [
        Input('deploystatus', 'n_clicks')
	],
    State("url", "search")
)

def deployStatus(n, search):
    ''' 
    This function will return status of testing
    Parameters:
        Input:
            url : Takes the url which contains uniqueid and modelname
        Output:
            status : status of testing
    '''
    deploy_status = ""
    
    # Extracting uniqueid from url search
    uniqueid = search.split('?')[1].split('&')[0].split('=')[1]
    
    res_dict = {}
    res_json = MakeJson(res_dict)

    if n:
        url = 'https://dldeploy.azurewebsites.net/getStatus/' + str(uniqueid)
        status = requests.get(url, json = res_json)
        deploy_status = status.json()
        n = None
        if deploy_status['status'].lower() == "completed":
            return html.Div(children = [html.Br(),html.H6(status.text),html.Br(),html.Br(),dbc.Button("Load Node-Red", id = 'node_red_button', color = "primary", className = "mr-1"),
			dbc.Button("Add DeployedModel to AutoAnnotation", id ='auto_annotate', color = "primary", className = "mr-1")])
        else:
            return status.text


# Callback for predict page
@app.callback(
    Output('dlservice_div', 'children'),
    [
        Input('dlservice', 'n_clicks'),
    ],
    State("url", "search")
)


def predict_page(dlservice_n, search):
    if dlservice_n:
        # Redirecting to predict page
        pathname = f"/predict"
        return dcc.Location(href = pathname, id = "dlserviceid")

@app.callback(
    Output('automodel_div', 'children'),
    [
        Input('auto_annotate','n_clicks')
	],
    State('url', 'search')
)

def autodiv_model(n, search):
    model_name = {}
    modelname = search.split('&')[1].split('=')[1]
    model_name['ModelName'] = modelname
    res_model = MakeJson(model_name)
    url = "https://20.81.152.2:5000/autoAnnotate"
    if n:
        status = requests.get(url, json = res_model, verify = False)
        if status.status_code == 200:
            return html.Div(children = [html.H6("AutoAnnotation model is completed for the deployed model"),html.Br(),html.Br()])
        else:
            return html.Div(children = [html.H6("AutoAnnotation model is failed for the deployed model"),html.Br(),html.Br()])

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
