# Importing all necessary libraries
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, State, Output
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.storage.blob import ContentSettings
import os
import base64
from urllib.parse import quote as urlquote
import json
import requests
import time

from ..app import app


connect_str = "DefaultEndpointsProtocol=https;AccountName=stdliopplatformdev001;AccountKey=Svo4kbk1P5GD4ES0IgWX4olyJq4MA75EEnz+QlPAaBFJOUk0RzblXKCEBgo3q5LeQktjg5Gw5lYP/2rSxiBcSA==;EndpointSuffix=core.windows.net"
UPLOAD_DIRECTORY = "/project/app_uploaded_files"

# Creating a temp directory
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)


# Layout for Testing Page
layout = html.Div([
    
    dcc.Location(id="url", refresh=False),

    # Creating a dynamic dropdown for modelname based on unique id
    dbc.Label("Model Name: "),
    dcc.Dropdown(
        id = "modelname",
        options = [{'label': 'foo', 'value': 'foo'}],
        searchable = False,
        multi = True,
    ),


    html.Div(id = "model-dropdown"),

    html.Br(),
    
    # Creating a uploading area
    dcc.Upload(
        id = "upload-data",
        children = html.Div(
            ["Drag and drop or select files to test"]
        ),
        style={
            "width": "100%",
            "height": "60px",
            "lineHeight": "60px",
            "borderWidth": "1px",
            "borderStyle": "dashed",
            "borderRadius": "5px",
            "textAlign": "center",
            "margin": "10px",
        },
        multiple = True
    ),
    html.Ul(id = 'uploadImages'),
    html.Hr(),

    html.Br(),
    
    # Creating a test button
    dbc.Button('Test', id = "test", color = "primary", className = "mr-1"),

    html.Div(id = 'output-image-upload')
])


# Saving file to Blob and returning URLs to Inference API
def save_file(name, content):
    os.chdir(UPLOAD_DIRECTORY)
    image_url = []
    if name.lower().endswith(('.png', '.jpg', '.jpeg')):
        data = content.encode("utf8").split(b";base64,")[1]

        # Loading files to temp directory
        with open(os.path.join(UPLOAD_DIRECTORY, name), "wb") as fp:
            fp.write(base64.decodebytes(data))
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        for files in os.listdir(UPLOAD_DIRECTORY):
            blob_client = blob_service_client.get_blob_client(container="oidlframework", blob ="Testing_Images/" + files)
            image_url.append(blob_client.url)
            # Uploding the image to blob
            with open(files, 'rb') as data:
                blob_client.upload_blob(data, overwrite=True, content_settings = ContentSettings(content_type='image/jpeg'))
        time.sleep(1)
        return image_url
    else:
        return "Please Upload image file"


# Callback for uploading images to temp directory and then to azure blob
@app.callback(
    Output('uploadImages', 'value'),
    [
        Input("upload-data", "filename"),
        Input("upload-data", "contents")
    ]
)

# Base function after uploading files
def update_output( uploaded_filenames, uploaded_file_contents):
    """Save uploaded files and regenerate the file list."""
    os.chdir(UPLOAD_DIRECTORY)
    remove_images()
    if uploaded_filenames is not None and uploaded_file_contents is not None:
        for i in range(len(uploaded_filenames)):
            if '.jpg' in uploaded_filenames[i] or '.JPG' in uploaded_filenames[i] or '.jpeg' in uploaded_filenames[i] or '.png' in uploaded_filenames[i] or '.PNG' in uploaded_filenames[i]:
                for name, data in zip(uploaded_filenames, uploaded_file_contents):
                    urls = save_file(name, data)
                return urls

# Removing files from the temp folder after uploading to blob every time
def remove_images():    
    os.chdir(UPLOAD_DIRECTORY)
    for images in os.listdir(UPLOAD_DIRECTORY): 
        os.remove(images)


# Callback for generating modelname based on uniqueid
@app.callback(
    Output('modelname', 'options'),
    [
        Input("model-dropdown", "value")
    ],
    State("url", "search")
)

def get_model_names(value, search):
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
    Output('modelname', 'value'),
    [
        Input("modelname", "options")
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

# Callback for accepting inputs from user
@app.callback(
    Output('output-image-upload', 'children'),
    [
        Input('modelname', 'value'),
        Input("uploadImages", "value"),
        Input('test', 'n_clicks')    
    ],
    State("url", "search")
)


def inference(modelname, uploadImages, n, search):
    '''
    This function will infer model on different images
    Parameters:
        Input:
            user inputs : Image(s) and model name
        Output:
            new tab : starts testing and returns to a teststatus page
    '''
    # Extracting unique id from url search
    uniqueid = search.split('?')[1].split('&')[0].split('=')[1]
    annotate_name = search.split('&')[1].split('=')[1]
    res_dict = {}
    res_dict["unique_id"] = str(uniqueid)

    # Input validation for modelname
    try:
        if len(modelname) > 0:
            res_dict["model_name"] = modelname
        else:
            raise Exception
    except Exception as e:
        return html.Div([
            f"No Models for this Uniqueid"
        ])
    res_dict["image_urls"] = uploadImages
    print(res_dict["image_urls"])

    # Checking whether the uploaded file is image or not
    if n:
        try:
            for i in range(len(res_dict["image_urls"])):
                if '.jpg' in res_dict["image_urls"][i] or '.jpeg' in res_dict["image_urls"][i] or '.png' in res_dict["image_urls"][i] or '.PNG' in res_dict["image_urls"][i]:
                    res_json = MakeJson(res_dict)
                else:
                    raise Exception
        except Exception as e:
            print(e)
            return html.Div([
                'Please Upload valid urls'
            ])
        print(res_json)
        remove_images()
        response = requests.post('https://dltesting.azurewebsites.net/getInference', json = res_json)
        
        # Redirecting to teststatus page
        pathname = f"/testStatus?uuid={uniqueid}&model={modelname}@name={annotate_name}"
        return dcc.Location(href = pathname, id = "testStatusid")

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
