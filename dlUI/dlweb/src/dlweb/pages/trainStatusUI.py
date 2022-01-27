# Importing all necessary libraries
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, State, Output
import plotly.graph_objs as go
import requests
import json
from flask import request

from ..app import app

# Layout for trainStatus page
layout = html.Div([
    dcc.Location(id="url", refresh=False),

    html.Br(),

    # Creating a button for getstatus of training
    dbc.Button('getStatus', id = "getstatus", color = "primary", className = "mr-1"),
    html.Div(id = 'status_div'),

    html.Br(),
    html.Br(),

    # Creates a button for testing
    dbc.Button('Testing', id = "testing", color = "primary", className = "mr-1"),
    html.Div(id = 'testing_div')
])


# Callback for getting training status
@app.callback(
    Output('status_div', 'children'),
    [
        Input('getstatus', 'n_clicks')
	],
    State("url", "search")
)

def getStatus(n, search):
    '''
    This function will return status of training
    Parameters:
        Input:
            url : Takes the url which contains runid and uniqueid 
        Output:
            status : status of training
    '''
    train_status = ""

    # Extracting runid from the url search
    runid = search.split('&')[0].split('=')[-1].lstrip("['%27").replace('%27]', '')
    print(runid)
    # Extracting uniqueid from url search
    uniqueid = search.split('&')[1].split('@')[0].split('=')[1]
    res_dict = {}
    res_dict['unique_id'] = uniqueid
    res_dict['run_id'] = runid
    res_json = MakeJson(res_dict)

    if n:
        without_loss = {}
        status_details = {}
        percent = {}
        url = 'https://dltraining.azurewebsites.net/getStatus/' + str(uniqueid)
        status = requests.get(url, json = res_json)
        json_status = status.json()
        if len(json_status) == 1:
            without_loss = json_status.copy()
            for key, value in without_loss.items():
                if without_loss[key] == "loss":
                    del without_loss['loss']
                else:
                    status_details['Status'] = without_loss['Status']['status']
                    n = None
            return html.Div(children = [html.Br(), html.H6(str(status_details).strip('{').strip('}').replace("'",""))])
        elif json_status['percent_done'] <= float(100.0):
            without_loss = json_status.copy()
            del without_loss['loss']
            status_details['Status'] = without_loss['Status']['status']
            percent['Done %'] = without_loss['percent_done']
            n = None
            return html.Div(children = [html.Br(), html.H6(str(status_details).strip('{').strip('}').replace("'","")), html.H6(str(percent).strip('{').strip('}').replace("'","")), dcc.Graph(
            id = 'losses_graph',
            figure=go.Figure(data = [go.Scatter(y = json_status['loss'])],layout={'title': {'text' : "Loss"}})
            )])
        else:
            without_loss = json_status.copy()
            for key, value in without_loss.items():
                if without_loss[key] == "loss":
                    del without_loss['loss']
                else:
                    status_details['Status'] = without_loss['Status']['status']
                    n = None
            return html.Div(children = [html.Br(), html.H6(str(status_details).strip('{').strip('}').replace("'",""))])

# Callback for redirecting to testing page
@app.callback(
    Output('testing_div', 'children'),
    [
        Input('testing', 'n_clicks')
	],
    State("url", "search")
)

def test_page(test_n, search):
    '''
    This function will redirects to testing page
    Parameters:
        Input:
            url : button click and url with uniqueid
        Output:
            New tab : redirects to testing page
    '''
    if test_n:
        uniqueid = search.split('&')[1].split('@')[0].split('=')[1]
        annotate_name = search.split('@')[1].split('=')[1]
        print(annotate_name)
        # Generating URL for the testing UI with uniqueid
        pathname = f"/getInference?uuid={uniqueid}&name={annotate_name}"
        n1=None
        return dcc.Location(href = pathname, id = "id12")


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
