# importing all necessary libraries
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, State, Output
import json
import requests
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient


from ..app import app

connect_str = "DefaultEndpointsProtocol=https;AccountName=stdliopplatformdev001;AccountKey=Svo4kbk1P5GD4ES0IgWX4olyJq4MA75EEnz+QlPAaBFJOUk0RzblXKCEBgo3q5LeQktjg5Gw5lYP/2rSxiBcSA==;EndpointSuffix=core.windows.net"

# Creating layout for deploy
layout = html.Div([

    dcc.Location(id="url", refresh=False),

    html.Br(),

    # Creating dropdown for modelname
    dbc.Label("Model Name: "),
    dcc.Dropdown(
        id = "modelnamedropdown",
        options = [{'label': "foo", 'value': "foo"}],
    ),

    html.Br(),
    
    # Creating radiobutton for deployment
    dbc.RadioItems(
        options = [
            {"label": "On Cloud", "value": "cloud"},
            {"label": "On EdgeDevice", "value": "edge"},
        ],
        value = "cloud",
        id = "radio_input",
        inline = True,
    ),

    html.Div(id = "modelName"),

    html.Div(id = "radiodiv"),

    html.Div(id="deploymentengine_dropdown"),

    html.Br(),

    # Creating deploy button 
    dbc.Button(children = 'Deploy', id = "deploy", color = "primary", className = "mr-1", n_clicks = 0),

    html.Div(id = 'cvat_ui'),

    html.Div(id = 'deploy_div_edge'),
])

# Callback for generating modelname based on uniqueid
@app.callback(
    Output('modelnamedropdown', 'options'),
    [
        Input('modelName', 'value'),
    ],
    State("url", "search")
)

def get_model_name(value, search):
    '''
    This function will return model names
    Parameters:
        Input:
            url : Takes the url which contains uniqueid 
        Output:
            model : returns the model name depends on uniqueid
    '''
    # Extracting uniqueid from the url search
    uniqueid = search.split('?')[1].split('&')[0].split('=')[1]
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    container_client = blob_service_client.get_container_client(container = 'oidlframework')
    blob_name = f'AppData/{uniqueid}/models/'
    blobs = container_client.list_blobs(name_starts_with = blob_name)
    directories = []
    models = []
    models_list = []
    # Getting the model names present in blobs for the selected uniqueid
    for directory in blobs:
        directories.append(directory.name)
    for model in directories:
        if len(model.split('/')) == 4:
            models.append(model)

    for model_name in models:
        models_list.append(model_name.split('/')[-1])
    print(models_list)

    return [{'label': modelName, 'value': modelName} for modelName in models_list]


# Callback for displaying and selecting the model name in the dropdown
@app.callback(
    Output('modelnamedropdown', 'value'),
    [
        Input("modelnamedropdown", "options")
    ]
)

def get_options(available_options):
    '''
    This function will return model names in dropdown
    Parameters:
        Input:
            available_options : has all the model names
        Output:
            options : returns options
    '''
    if available_options:
        return available_options[0]['value']
    else:
        pass


# Callback for generating modelname based on uniqueid and selecting the deployment on cloud or edge
@app.callback(
    Output('radiodiv', 'children'),
    [
        Input('radio_input', 'value'),
        Input('modelnamedropdown', 'value'),
        Input('deploy', 'n_clicks')
    ],
    State("url", "search")
)

def radio_selected(radiovalue, modelnamedropdown, n, search):
    '''
    This function will return model names in dropdown and does the required function when the user selects edge or cloud
    Parameters:
        Input:
            radio_value : type of deployment selected
            modelnamedropdown : has all the model names
            n : Deploy button
			search : seach string in URL
        Output:
            options : returns options
			children : returns the UI based on radio input selected and after clicked on deploy
    '''
    devicelist = []
	# If the radio button selected is cloud
    if radiovalue == "cloud":
        uniqueid = search.split('?')[1].split('&')[0].split('=')[1]
        annotate_name = search.split('&')[1].split('=')[1]
        res_dict = {}
        res_dict['unique_id'] = str(uniqueid)
	    
        # Input validation for modelname
        try:
            if len(modelnamedropdown) > 0:
                res_dict['model_name'] = modelnamedropdown
            else:
                raise Exception
        except Exception as e:
            return html.Div([
                f"No Models for this Uniqueid"
            ])
        if n:
            deploy_json = MakeJson(res_dict)
            url = 'https://dldeploy.azurewebsites.net/deployModel'
            status = requests.post(url, json=deploy_json)
            pathname = f"/deployStatus?uuid={res_dict['unique_id']}&name={annotate_name}"
            n = 0
            return dcc.Location(href = pathname, id = "deploystatusid")
	# If the radio button selected is edge
    elif radiovalue == "edge":
        devices = requests.get("https://dlframeworkhub.azure-devices.net/devices?api-version=2018-06-30", headers={'Authorization':'SharedAccessSignature sr=DLFrameworkHub.azure-devices.net&sig=Q0kW1W8zayw8S5RsyMoBXfLvGMkxtF1uiXAMrYCaci8%3D&se=1626873381&skn=iothubowner'})
        if devices.status_code:
            for dicts in devices.json():
                if type(dicts) is dict:
                    if dicts['connectionState'] == 'Connected':
                        devicelist.append(dicts['deviceId'])
		# Returns a dropdown of all the available deployment engines in IOT
        return html.Div(children = [html.Br(),dbc.Label("Deployment Engines: "),dcc.Dropdown(id = 'deploymentengine_dropdown', options = [{'label': device, 'value': device} for device in devicelist])])

# Callback for generating dropdown of all the available deployment engines in IOT
@app.callback(
    Output('deploymentengine_dropdown', 'value'),
    [
        Input("deploymentengine_dropdown", "options")
    ]
)

def get_options(available_options):
    '''
    This function will return deployment engine names in dropdown
    Parameters:
        Input:
            available_options : has all the deployment engine names
        Output:
            options : returns options
    '''
    if available_options:
        return available_options[0]['value']
    else:
        pass

# Callback to deploy on edge after selecting the deployment engine	
@app.callback(
    Output('deploy_div_edge', 'children'), 
    [
        Input('radiodiv', 'value'),
        Input('deploymentengine_dropdown', 'value'),
        Input('deploy', 'n_clicks')
    ],
    State("url", "search")
)

def enginedropdown(available_options, value, n, search):
    '''
	This function will return deployment engine names in dropdown
	Parameters:
		Input:
			available_options : has all the deployment engine names
		Output:
			options : returns options
    '''
    uniqueid = search.split('?')[1].split('&')[0].split('=')[1]
    annotate_name = search.split('&')[1].split('=')[1]
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_client = blob_service_client.get_blob_client(container = 'oidlframework', blob = 'Configs/deployment.amd64.json')
    with open('./'+'deployment.amd64.json', 'wb') as data:
        try:
            # Downloading stream of config data
            download_stream = blob_client.download_blob()
            # Writing it in a config file
            data.write(download_stream.readall())
            # Reading the config into a JSON dict
            config = json.loads(download_stream.readall())
            # Closing the stream
            data.close()
        except Exception as e:
            print("Blob not found with given name")
    with open('./'+'deployment.amd64.json', 'r') as iotfile:
        deployiot = iotfile.read()
        deployiotconfig = json.loads(deployiot)

    url_to_deploy_on_edge = "https://dlframeworkhub.azure-devices.net/devices/"+ str(value) +"/applyConfigurationContent?api-version=2018-06-30"
    print(url_to_deploy_on_edge)
    if n:
        status = requests.post(url_to_deploy_on_edge, json=deployiotconfig, headers={'Authorization':'SharedAccessSignature sr=DLFrameworkHub.azure-devices.net&sig=Q0kW1W8zayw8S5RsyMoBXfLvGMkxtF1uiXAMrYCaci8%3D&se=1626873381&skn=iothubowner'})
        pathname = f"/deployStatus?uuid={str(uniqueid)}&name={annotate_name}"
        print(status.status_code)
        if status.status_code == 204:
            return html.Div(children = [dcc.ConfirmDialog(id='confirm', message = "Model is deployed on selected Edge Device, redirecting to home page!!!!!")])


# Callback for getting Message box
@app.callback(
    Output('confirm', 'displayed'),
    [
        Input('deploy', 'n_clicks'),
    ]
)


def display_confirm(n):
    '''
	This function will getting Message box after clicking on deploy using edge
	Parameters:
		Input:
			n_clicks : deploy button clicks
		Output:
			MessageBox : returns MessageBox
    '''
    if n:
        return True
    return False

# Callback to redirect to CVAT UI
@app.callback(
    Output('cvat_ui', 'children'),
    [
        Input('confirm', 'submit_n_clicks'),
    ]
)


def update_output(submit_n_clicks):
    '''
	This function will redirect to CVAT UI after clicking on deploy using edge
	Parameters:
		Input:
			n_clicks : after clicking on OK in message box.
		Output:
			CVAT UI : returns CVAT UI
    '''
    if submit_n_clicks:
        return dcc.Location(href='http://20.81.152.2:8080/tasks', id="id123")


def MakeJson(res_dict):
    '''
    This function will return the json file 
    Parameters:
        Input:
            dictionary : dictionary with all user inputs
        Output:
            config : resultant Inputs in JSON format which will be given as input to request.
    '''
    load_json = json.dumps(res_dict, indent = 4)
    res_json = json.loads(load_json)
    return res_json

