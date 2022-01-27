# Import utilites
from numpy.lib.arraysetops import unique
from utils import label_map_util
from utils import visualization_utils as vis_util# Importing Packages
from azure.storage.blob import BlobServiceClient
from database import get_azure_config
import json
import os
import cv2
import requests
import numpy as np
import tensorflow as tf
import sys
import azure
import base64
from skimage import io

# Getting azure credentials
oiazurecred = get_azure_config()

def init():
    global model_name
    global MODEL_NAME
    global PATH_TO_CKPT
    global PATH_TO_CKPT
    global label_map
    global NUM_CLASSES


    # Name of the directory containing the object detection module we're using
    model_name = [name for name in os.listdir(os.path.join(os.getenv('AZUREML_MODEL_DIR'), './models')) if os.path.isdir(os.path.join(os.getenv('AZUREML_MODEL_DIR'), './models', name))][0]
    MODEL_NAME = os.path.join(os.getenv('AZUREML_MODEL_DIR'), './models', model_name)

    # Path to frozen detection graph .pb file, which contains the model that is used
    # for object detection.
    PATH_TO_CKPT = os.path.join(MODEL_NAME,'frozen_inference_graph.pb')

    # Path to label map file
    PATH_TO_LABELS = os.path.join(MODEL_NAME,'label_map.pbtxt')

    # Load the label map.
    label_map = label_map_util.load_labelmap(PATH_TO_LABELS)

    # Number of classes the object detector can identify
    NUM_CLASSES = len(label_map.item)



def run(raw_data):

    # Getting unique_id
    with open(os.path.join(os.getenv('AZUREML_MODEL_DIR'), './models', 'DeployConfig.json'),'rb') as _data:
        unique_id = json.load(_data)['unique_id']

    # Initializing the function response
    response = {}
    _scores = []
    temp_dict = {}
    api_response = {}

    # Getting the  image  url from the data object
    urls = json.loads(raw_data)['data']
    print(urls)

    for url in urls:

        # Checking the url provided
        check_url_flag, check_valid_img_flag = check_url(url)

        if not(check_url_flag):
            response = {
                'status' : 'Exception',
                'message'  : 'Invalid URL'
            }

        elif not(check_valid_img_flag):
            response = {
                'status' : 'Exception',
                'message'  : 'URL does not point to a valid image source'
            }
        else:

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
                print(tf.__version__)
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
            image = io.imread(url)
            # image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_expanded = np.expand_dims(image, axis=0)

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
                line_thickness=25,
                min_score_thresh=0.70)

            # Uplaod images to azure blob storage
            inference_url = upload_infered_images(image, unique_id, model_name, url)

            # Initializing the return variables
            score_list = []
            box_list = []
            class_list = []

            for index, value in enumerate(classes[0]):
                if scores[0, index] > 0.50:
                    score_list.append(scores[0, index])
                    box_list.append(boxes[0][index])
                    class_list.append(str(category_index.get(value).get('name')))

            response['infered_img'] = inference_url
            response['score'] = [np.float(score) for score in score_list],
            response['class'] = class_list
            response['box'] = [[np.float(num) for num in list(box)] for box in box_list]


            api_response[url] = response
            _scores.append(api_response[url]['score'][0])

    score_list = [item for sublist in _scores for item in sublist]
    mean_score = np.mean(score_list)
    api_response['Avg Score'] = mean_score
    return api_response


# Function to check the url provided
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