# Importing all necessary libraries
from collections import Counter
from textwrap import dedent

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, State, Output
import json
import requests
import time
from flask import redirect
from ..app import app
import urllib
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient


connect_str = "DefaultEndpointsProtocol=https;AccountName=stdliopplatformdev001;AccountKey=Svo4kbk1P5GD4ES0IgWX4olyJq4MA75EEnz+QlPAaBFJOUk0RzblXKCEBgo3q5LeQktjg5Gw5lYP/2rSxiBcSA==;EndpointSuffix=core.windows.net"

models_dict = {}
def get_layout(**kwargs):
    initial_text = kwargs.get("text", "Type some text into me!")

    # Layout for training page
    return html.Div(
        [
            # Represents the URL bar, doesn't render anything
            dcc.Markdown(
                dedent(
                    """
                    # DL Web UI
                    
                    Training and Predicting the Images
                    """
                )
            ),
            dbc.FormGroup(
                [
                    dcc.Location(id="url", refresh=True),

                    # Creating a dropdown for models
                    dbc.Label("Models: "),
                    dcc.Dropdown(
                        id = 'model',
                        options=[
                            {'label' : 'foo', 'value' : 'foo'},
                        ],
                        searchable = False,
                        placeholder = 'Select a Model',
                        multi = True
                    ),

                    html.Div(id = "dropdown_model"),
                    html.Br(),

                    # Creating Radio Buttion for CPU/GPU
                    dbc.Label("GPU/CPU: "),
                    dbc.RadioItems(
                        id = 'cpuorgpu',
                        options=[
                            {'label' : "CPU", 'value' : 0},
                            {'label' : "GPU", 'value' : 1},
                        ],
                        value = 1,
                        inline = True,
                    ),

                    html.Br(),

                    # Creating a Text box for Epochs
                    dbc.Label("Epochs: "),
                    dbc.Input(id = "epochs", placeholder = "Enter the number of epochs", type = "number"),
                    html.Br(),
                    
                    # Creating a Text box for Learning Rate
                    dbc.Label("Learning Rate: "),
                    dbc.Input(id = "learningrate", placeholder = "Enter the LearningRate", type = "number"),
                    html.Br(),
                    
                    # Creating a Text box for Batch size
                    dbc.Label("Batch Size: "),
                    dbc.Input(id = "batchsize", placeholder = "Enter the number of batches", type = "number"),
                    html.Br(),

                    # Creating a dropdown for Data Augmentation
                    dbc.Label("Data Augmentation: "),
                    dcc.Dropdown(
                        id = 'dataaugment',
                        options=[
                            {'label' : 'foo', 'value' : 'foo'},
                        ],
                        searchable = False,
                        placeholder = 'Select Data Augment type',
                        multi = True
                    ),

                    html.Div(id = "dataaugment_type"),

                ]
            ),
            dbc.FormGroup(
                [
                        # Creating a button for Train
                        dbc.Button("Train", id = 'train-button', color = "primary", className = "mr-1")
                ]
            ),
            html.Div(id = 'output_div'),
        ]
    )


# Creating callbacks for model selection
@app.callback(
    Output('model', 'options'),
    [
        Input("dropdown_model", "value")
    ]
)

def update_modelname(value):
    '''
    This function will returns modelnames from the modelSelection API  
    Parameters:
        Input:
            Json : json response of the modelselection API
        Output:
            modelname : returns modelnames from the modelSelection API
    '''
    response = requests.get("https://dlmodelselection.azurewebsites.net/getModels")
    models = response.json()
    models_dict.update(models)
    model_list = []
    temp_dict = {}
    for keys, values in models.items():
        if type(values) is dict:
            temp_dict.update(values)
            for key, value in temp_dict.items():
                model_list.append(value['Name'])
    
    return [{'label' : modelName, 'value' : modelName} for modelName in model_list]


# Creating callbacks for data augment options
@app.callback(
    Output('dataaugment', 'options'),
    [
        Input("dataaugment_type", "value")
    ]
)

def update_dataaugment(value):
    '''
    This function will returns augment options from the OIConfig.json file  
    Parameters:
        Input:
            Json : OIConfig.json file
        Output:
            dataaugment_options : returns dataaugment options
    '''
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_client = blob_service_client.get_blob_client(container = 'oidlframework', blob = 'Configs/OIConfig.json')
    with open('./'+'OIConfig.json', 'wb') as data:
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

    data_augment_options = config['preprocess'].split(",")
    
    return [{'label' : data_augment, 'value' : data_augment} for data_augment in data_augment_options]

# Creating callbacks for epoch
@app.callback(
    Output('epochs', 'value'),
    [
        Input("model", "value")
    ]
)

def update_epoch(model):
    '''
    This function will returns epochs based on model  
    Parameters:
        Input:
            model : model selected by user
        Output:
            epochs : returns epochs on UI
    '''
    params_dict = {}
    try:
        if len(model) > 0:
            for keys, values in models_dict.items():
                if type(values) is dict:
                    params_dict.update(values)
                    for key, value in params_dict.items():
                        if value['Name'] == model[0]:
                            epochs = value['Parameters']['Epochs']
            
                    return epochs
        else:
            raise Exception
    except Exception as e:
        return f"Please Select Model"


# Creating callbacks for LearningRate
@app.callback(
    Output('learningrate', 'value'),
    [
        Input("model", "value")
    ]
)

def update_lr(model):
    '''
    This function will returns LearningRate based on model  
    Parameters:
        Input:
            model : model selected by user
        Output:
            learningrate : returns learningrate on UI
    '''

    params_dict = {}
    try:
        if len(model) > 0:
            for keys, values in models_dict.items():
                if type(values) is dict:
                    params_dict.update(values)
                    for key, value in params_dict.items():
                        if value['Name'] == model[0]:
                            lr = value['Parameters']['LearningRate']
            
                    return lr
        else:
            raise Exception
    except Exception as e:
        return f"Please Select Model"


# Creating callbacks for BatchSize
@app.callback(
    Output('batchsize', 'value'),
    [
        Input("model", "value")
    ]
)

def update_batchsize(model):
    '''
    This function will returns batchsize based on model  
    Parameters:
        Input:
            model : model selected by user
        Output:
            batchsize : returns batchsize on UI
    '''
    try:
        if len(model) > 0:
            return 1
        else:
            raise Exception
    except Exception as e:
        return f"Please Select Model"

# Creating callbacks for user input 
@app.callback(
    Output("output_div", "children"),
    [
        Input("model", "value"),
        Input("cpuorgpu", "value"),
        Input("epochs", "value"),
        Input("learningrate", "value"),
        Input("batchsize", "value"),
        Input("dataaugment", "value"),
        Input("train-button", "n_clicks")
    ],
    State("url", "search")
)

def update_output_div(model, cpuorgpu, epoch, learningRate, batchSize, dataaugment, n, search):
    '''
    This function will start training with all the user given inputs
    Parameters:
        Input:
            variables : all the user defined values
        Output:
            train status page : redirects to train status page with runid and uniqueid
    '''
    status = ""
    unique_id = search.split('&')[0].split('?')[1].split('=')[1]
    annotate_name = search.split('&')[1].split('=')[1].replace('%20','_').lower()
    res_dict = {}
    epochs = []
    lr = []
    gpuorcpu = []
    batch_size = []
    augmentoptions = []
    unique_id = str(unique_id)  
    gpuorcpu.append(cpuorgpu)
    res_dict['unique_id'] = str(unique_id)

    # Input validation for model
    try:
        if len(model)>0:
            res_dict['models'] = model
        else:
            raise Exception
    except Exception as e:
        return "Please Select a model"
    res_dict['gpu'] = gpuorcpu
    

    # Input validation for Epoch
    try:
        if epoch>0:
            epochs.append(epoch)
        else:
            raise Exception
    except Exception as e:
        return "Epochs cannot be zero or negative"


    # Input validation for Learning Rate
    try:
        if learningRate>0:
            lr.append(learningRate)
        else:
            raise Exception
    except Exception as e:
        return "Learning Rate cannot be zero or negative"
    

    # Input validation for Batchsize
    try:
        if batchSize>0:
            batch_size.append(batchSize)
        else:
            raise Exception
    except Exception as e:
        return "Batch Size cannot be zero or negative"

    # Input validation for dataaugmentation
    if dataaugment:
        res_dict['augment_options'] = dataaugment
    else:
        res_dict['augment_options'] = augmentoptions
    
    res_dict['epochs'] = epochs
    res_dict['batch_size'] = batch_size
    res_dict['lr'] = lr

    if n:
        result = on_button_click(n, res_dict) 
        response_dict = dict(result.json())

    # Redirects page to trainstatus with runid and uniqueid
        pathname = f"/trainStatus?run_id={response_dict['RunID']}&uuid={unique_id}@name={annotate_name}"
        n = 0
        return dcc.Location(href=pathname, id="id123")


def on_button_click(n, res_dict):
    '''
    This function will starts training  
    Parameters:
        Input:
            dictionary : dictionary with all user inputs
        Output:
            response : response of the request of training
    '''
    loaded_json = MakeJson(res_dict)
    result = requests.post('https://dltraining.azurewebsites.net/initiateTraining',json=loaded_json)
    return result

def MakeJson(res_dict):
    '''
    This function will return the json file 
    Parameters:
        Input:
            dictionary : dictionary with all user inputs
        Output:
            config : resultant Inputs in JSON format which will be given as input to request.
    '''
    res_json = json.dumps(res_dict, indent=4)
    print(res_json)
    loaded_json = json.loads(res_json)
    return loaded_json

