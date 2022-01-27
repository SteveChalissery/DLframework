# Import utilites
from utils import label_map_util
from utils import visualization_utils as vis_util# Importing Packages
import json
from database import get_azure_config
import requests
import exception
import os
import cv2
import numpy as np
import tensorflow as tf
import sys
import azure
import base64
from PIL import Image


# Import utilites
from utils import label_map_util
from utils import visualization_utils as vis_util
from azure.storage.blob import BlobServiceClient


# Getting azure credentials
oiazurecred = get_azure_config()

with open('OIConfig.json', 'rb') as data:
    oiconfig = json.load(data)

# Check whether the url is valid and points to an image
def check_url(url):
    """Returns True if the url returns a response code between 200-300,
       otherwise return False.
    """
    is_url = False
    is_image = False

    request_headers = requests.head(url)
    request_url = requests.get(url)

    if request_url.status_code == 200:
        is_url = True
    
    # If the url is valid then check the content-type
    if is_url:
        if str(request_headers.headers["content-type"]).startswith('image'):
            is_image = True

    return is_url, is_image


# Function to load the tensorflow model
def do_inference(image):
    # Name of the directory containing the object detection module we're using
    MODEL_NAME = 'models'

    # Path to model directory
    CWD_PATH = "/usr/deployedModel"

    # Path to frozen detection graph .pb file, which contains the model that is used
    # for object detection.
    PATH_TO_CKPT = os.path.join(CWD_PATH,MODEL_NAME,'frozen_inference_graph.pb')

    # Path to label map file
    PATH_TO_LABELS = os.path.join(CWD_PATH,MODEL_NAME,'label_map.pbtxt')
    
    try:
        # Getting the deployement model details
        unique_id, model_name = get_deployement_details()

    #     # Downloading the model from azure
    #     download_model(unique_id, model_name)
    except:
        raise exception.ResourceNotFound

    # Load the label map.
    label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
    # Number of classes the object detector can identify
    NUM_CLASSES = len(label_map.item)

    categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
    category_index = label_map_util.create_category_index(categories)

    # Load the Tensorflow model into memory.
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')
        sess = tf.Session(graph=detection_graph)

    # Define input and output tensors (i.e. data) for the object detection classifier

    # # Input tensor is the image
    image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')

    # Output tensors are the detection boxes, scores, and classes
    # Each box represents a part of the image where a particular object was detected
    detection_boxes = detection_graph.get_tensor_by_name('detection_boxes:0')

    # Each score represents level of confidence for each of the objects.
    # The score is shown on the result image, together with the class label.
    detection_scores = detection_graph.get_tensor_by_name('detection_scores:0')
    detection_classes = detection_graph.get_tensor_by_name('detection_classes:0')

    # Number of objects detected
    num_detections = detection_graph.get_tensor_by_name('num_detections:0')

    # Load image using OpenCV and
    # expand image dimensions to have shape: [1, None, None, 3]
    # i.e. a single-column array, where each item in the column has the pixel RGB value
    image = np.float32(image)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_expanded = np.expand_dims(image_rgb, axis=0)

    # Perform the actual detection by running the model with the image as input
    (boxes, scores, classes, num) = sess.run(
        [detection_boxes, detection_scores, detection_classes, num_detections],
        feed_dict={image_tensor: image_expanded})

    vis_util.visualize_boxes_and_labels_on_image_array(
        image,
        np.squeeze(boxes),
        np.squeeze(classes).astype(np.int32),
        np.squeeze(scores),
        category_index,
        use_normalized_coordinates=True,
        line_thickness=1,
        min_score_thresh=0.60)

    # # Uplaod images to azure blob storage
    # inference_url = upload_infered_images(image, unique_id, model_name, url)
    
    # Initializing the return variables
    response = {}
    score_list = []
    box_list = []
    class_list = []

    for index, value in enumerate(classes[0]):
        if scores[0, index] > 0.60:
            score_list.append(scores[0, index])
            box_list.append(boxes[0][index])
            class_list.append(str(category_index.get(value).get('name')))
    import io
    image = Image.fromarray(np.uint8(image))
    output_buffer = io.BytesIO()
    image.save(output_buffer, format='JPEG')
    byte_data = output_buffer.getvalue()
    image = base64.b64encode(byte_data).decode('utf-8')
    
    response['infered_img'] = image
    response['score'] = [np.float(score) for score in score_list],
    response['class'] = class_list
    response['box'] = [[np.float(num) for num in list(box)] for box in box_list]

    return response

def get_deployement_details():

    # Initializing return variables
    unique_id = ""
    model_name = ""

    # Service client of azure to connect to blob storage
    blob_service_client = BlobServiceClient.from_connection_string(oiazurecred['blobconnectionstring'])

    blob_path = "DeployConfig.json"

    # Holder of the config file
    blob_client = blob_service_client.get_blob_client(container=oiazurecred['blobcontainername'], 
                                                        blob=blob_path)

    # Writing the data in the file to local folder
    with open('DeployConfig.json', 'wb') as data:
        try:
            # Downloading stream of config data
            download_stream = blob_client.download_blob()
            # Writing it in a config file
            data.write(download_stream.readall())
            # Closing the stream
            data.close()
        except azure.core.exceptions.ResourceNotFoundError:
            raise exception.ResourceNotFound


    if (os.path.exists(f"DeployConfig.json")):
        with open('DeployConfig.json', 'rb') as data:
        
            deployData = json.loads(data.readlines()[0])
            unique_id = deployData['unique_id']
            model_name = deployData['Model Name']

    return unique_id, model_name

# Function to download the model locally
def download_model(unique_id, model_name):
    # Service client of azure to connect to blob storage
    blob_service_client = BlobServiceClient.from_connection_string(oiazurecred['blobconnectionstring'])

    blob_path = oiazurecred['blobcontainername'] + "/" + str(unique_id) + "/models/" + str(model_name) + "/model/frozen_inference_graph.pb"

    # Holder of the config file
    blob_client = blob_service_client.get_blob_client(container=oiazurecred['blobcontainername'], 
                                                        blob=blob_path)

    if not os.path.exists("models"):
        os.mkdir("models")

    # Writing the data in the file to local folder
    with open('models'+'/frozen_inference_graph.pb', 'wb') as data:
        try:
            # Downloading stream of config data
            download_stream = blob_client.download_blob()
            # Writing it in a config file
            data.write(download_stream.readall())
            # Closing the stream
            data.close()
        except azure.core.exceptions.ResourceNotFoundError:
            raise exception.ResourceNotFound

    # Downloading the labelmap
    blob_path = oiazurecred['blobcontainername'] + "/" + str(unique_id) + "/annotations/tfrecords/label_map.pbtxt"

    # Holder of the config file
    blob_client = blob_service_client.get_blob_client(container=oiazurecred['blobcontainername'], 
                                                        blob=blob_path)

    # Writing the data in the file to local folder
    with open('models/'+'label_map.pbtxt', 'wb') as data:
        try:
            # Downloading stream of config data
            download_stream = blob_client.download_blob()
            # Writing it in a config file
            data.write(download_stream.readall())
            # Closing the stream
            data.close()
        except azure.core.exceptions.ResourceNotFoundError:
            
            ("Blob not found with given name")

# Function to upload the infered images to azure blob
def upload_infered_images(img, unique_id, model_name, img_url):
    img_name = str(img_url).split('/')[-1]
    cv2.imwrite(img_name, img)

    # Service client of azure to connect to blob storage
    blob_service_client = BlobServiceClient.from_connection_string(oiazurecred['blobconnectionstring'])
    
    # Path to store the model
    blob_client = blob_service_client.get_blob_client(container=oiazurecred['blobcontainername'], 
                                    blob=oiazurecred['blobcontainername'] + "/" +str(unique_id) + "/inference/models/" + str(model_name) + "/Images/" + img_name)

    # Uploding the image
    with open(img_name, 'rb') as data:
        blob_client.upload_blob(data, overwrite=True)
    
    return blob_client.url
    

# Function to update the status 
def update_status(unique_id, exception_obj=None, status='Exception'):
    '''
    Function to update the status file when an exception occurs.
    Parameters:
        Input:
            unique_id : Unique Id to find the status file.
            exception_obj : Exception obj
            status : Writing reason for the update
        Output:
            None : Returns nothing
    '''
    if status == 'Exception':
        with open(unique_id + '_status.json', 'w') as data:
            # Creating response dict
            response_dict = {
                'status' : status,
                'response' : {
                    'Class' : str(exception_obj.__class__),
                    'Message' : str(exception_obj)
                }
            }
            data.write(json.dumps(response_dict))
            data.close()
    
    if status == 'Started':
        with open(unique_id + '_status.json', 'w') as data:
            # Creating response dict
            response_dict = {
                'status' : status,
                'response' : {}
            }
            data.write(json.dumps(response_dict))
            data.close()

    if status == 'Starting':
        with open(unique_id + '_status.json', 'w') as data:
            # Creating response dict
            response_dict = {
                'status' : status,
                'response' : {}
            }
            data.write(json.dumps(response_dict))
            data.close()
