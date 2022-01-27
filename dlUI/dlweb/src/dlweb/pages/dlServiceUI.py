# importing all necessary directores
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, State, Output
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import ContentSettings
import os
import base64
from urllib.parse import quote as urlquote
import json
import requests
import time
from flask import jsonify

from ..app import app

connect_str = "DefaultEndpointsProtocol=https;AccountName=stdliopplatformdev001;AccountKey=Svo4kbk1P5GD4ES0IgWX4olyJq4MA75EEnz+QlPAaBFJOUk0RzblXKCEBgo3q5LeQktjg5Gw5lYP/2rSxiBcSA==;EndpointSuffix=core.windows.net"
UPLOAD_DIRECTORY = "/project/app_uploaded_files"

#Creating a temp directory
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

#View for dlservice Page 
layout = html.Div([

    # Creating a uploading area
    dcc.Upload(
        id = "upload-data",
        children = html.Div(
            ["Select file to provide input to AI Model"]
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
    html.Ul(id = 'uploadImage'),
    html.Hr(),

    html.Br(),
    
    # Creating a predict button
    dbc.Button('Submit', id = "submit", color = "primary", className = "mr-1"),

    html.Div(id = 'body-image')
])


#Saving file to Blob and returning URLs to Inference API
def save_file(name, content):
    os.chdir(UPLOAD_DIRECTORY)
    image_url = []
    """Decode and store a file uploaded with Plotly Dash."""
    data = content.encode("utf8").split(b";base64,")[1]

    # Loading files to temp directory
    with open(os.path.join(UPLOAD_DIRECTORY, name), "wb") as fp:
        fp.write(base64.decodebytes(data))
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    for files in os.listdir(UPLOAD_DIRECTORY):
        blob_client = blob_service_client.get_blob_client(container="oidlframework", blob ="" + "Dataset/" + files)
        image_url.append(blob_client.url)
        # Uploding the image to blob
        with open(files, 'rb') as data:
            blob_client.upload_blob(data, overwrite=True, content_settings = ContentSettings(content_type='image/jpeg'))
    return image_url

# Callback for uploading images to temp directory and then to azure blob
@app.callback(
    Output('uploadImage', 'value'),
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

# Callback for predicting image
@app.callback(
    Output('body-image', 'children'),
    [
        Input("uploadImage", "value"),
        Input('submit', 'n_clicks')        
    ]
)


def predict(uploadImage, n):
    '''
    This function will return model names
    Parameters:
        Input:
            image : Takes the image which you want to predict 
        Output:
            image : return image with bounding boxes on top of it
    '''
    if uploadImage:
        res_dict = {}
        res_dict["image_urls"] = uploadImage
        _data = {}
        _data['data'] = "{\"data\": [\""+ str(uploadImage[0]) + "\"]}"

        # Checking whether the uploaded file is image or not
        if n:
            try:
                for i in range(len(res_dict["image_urls"])):
                    if '.jpg' in res_dict["image_urls"][i] or '.jpeg' in res_dict["image_urls"][i] or '.png' in res_dict["image_urls"][i] or '.PNG' in res_dict["image_urls"][i]:
                        res_json = MakeJson(_data)
                        test_status = on_button_click(n, res_json)
                        return test_status
                    else:
                        raise Exception
            except Exception as e:
                print(e)
                return html.Div([
                    'Please Upload Images with extension either .jpg or .png'
                ])
    
def on_button_click(n, res_json):
    '''
    This function will return the result image 
    Parameters:
        Input:
            button click : on button click
        Output:
            image : return image with bounding boxes on top of it
    '''
    if n:
        remove_images()
        res_image= ""
        status = requests.post('https://dlinference.azurewebsites.net/imageinference', json = res_json)
        image_link =  json.loads(status.text)
        print(image_link)
        for key, value in image_link.items():
            res_image = value['infered_img']
            break

        return html.Img(src = str(res_image), style = {
            "height" : "500px",
            "width" : "500px"
        })            


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
