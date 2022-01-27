r"""Wrapper to call Tensorflow object detection model training. 

Example usage:
    ./train \
        --checkpoint_dir=path/to/train_checkpoints \
        --model_config_path=path/to/pipeline.config \
        --num_steps=number_of_train_steps \
        --export_dir=path/to/exported_model
"""
import argparse
import sys
import os

from object_detection import exporter
from object_detection.utils import config_util
from object_detection.utils import label_map_util


from azureml.core import Run

import logging
import logging.config
import yaml
import subprocess
import shutil

import tensorflow as tf

logger = None
run = Run.get_context()

os.sep = '/'

parser = argparse.ArgumentParser()
parser.add_argument('--base_model_dir', 
                    help='Path to a downloaded base model which contains model.ckpt and pipeline.config.',
                    required=True)
parser.add_argument('--tfrecords_dir', 
                    help='Path to tfrecords and pascal label map to train on.',
                    required=True)
parser.add_argument('--num_steps', type=int, 
                    help='Number of train steps.',
                    default=20000)
parser.add_argument('--learning_rate', 
                    help='Learning rate to train the model on.',
                    default=1e-10)  
parser.add_argument('--batch_size', 
                    help='Batch size for training images',
                    default=2)                  
parser.add_argument('--force_regenerate_tfrecords', type=bool, 
                    help='Whether to regenerate TFRecords even if no changes detected',
                    default=False)
parser.add_argument('--output_dir', 
                    help='The exported model will be save under model subfolder for inferencing.',
                    default='outputs')  
parser.add_argument('--log_dir', 
                    help='Path to logs, training checkpoints will be save under model subfolder.',
                    default='logs')  
parser.add_argument('--classname_in_filename', type=bool,
                    help='Whether or not the object class name is in the filename instead of annotation xml.',
                    default=False) 
parser.add_argument('--data_augment_options', 
                    help='The data augmentation options',
                    default='null')                
 
FLAGS = parser.parse_args()

def update_pipeline_config():
  org_pipeline_config_file = os.path.join(FLAGS.base_model_dir.replace("\\", '/').replace("//", ''), 'pipeline.config')
        
  logger.info('original pipeline.config {}'.format(org_pipeline_config_file))
  cfg = config_util.get_configs_from_pipeline_file(org_pipeline_config_file)

  #update num_of_classe
  model_name = os.path.basename(os.path.normpath(FLAGS.base_model_dir)).lower()
  if "ssd" in model_name:
    model_cfg = cfg['model'].ssd
    logger.info('found a ssd base model')
  elif "faster_rcnn" in model_name:
    model_cfg = cfg['model'].faster_rcnn
    logger.info('found a faster_rcnn base model')
  else:
    raise ValueError('unknown base model {}, we can only handle ssd nor faster_rcnn'.format(model_name))


  label_map_file = os.path.join(FLAGS.tfrecords_dir.replace("\\", '/').replace("//", ''), 'label_map.pbtxt') 
  label_map_dict = label_map_util.get_label_map_dict(label_map_file)
  num_classes = len(label_map_dict)
  logger.info('num_of_classes from {} to {}'.format(model_cfg.num_classes, num_classes))
  model_cfg.num_classes = num_classes

  #update base_model_dir
  train_cfg = cfg['train_config']
  train_cfg.fine_tune_checkpoint = os.path.join(str(FLAGS.base_model_dir).replace("\\", '/'), 'model.ckpt')
  logger.info('fine_tune_checkpoint: {}'.format(train_cfg.fine_tune_checkpoint))
  
  #update num_train_steps, label_map_path, train_tfrecords, val_tfrecords
  hparams = tf.contrib.training.HParams(
    batch_size=int(FLAGS.batch_size),
    train_steps=int(FLAGS.num_steps),
    label_map_path=label_map_file,
    train_input_path=os.path.join(str(FLAGS.tfrecords_dir).replace("\\", '/'), 'default.tfrecord'),
    eval_input_path=os.path.join(str(FLAGS.tfrecords_dir).replace("\\", '/'), 'default.tfrecord'))
  cfg = config_util.merge_external_params_with_configs(cfg, hparams)

  updated_pipeline_config = config_util.create_pipeline_proto_from_configs(cfg)
  updated_pipeline_config_file = os.path.join(FLAGS.output_dir.replace("\\", '/').replace("//", ''), 'pipeline.config')
  config_util.save_pipeline_config(updated_pipeline_config, FLAGS.output_dir.replace("\\", '/').replace("//", ''))
  logger.info('updated pipeline.config {}'.format(FLAGS.output_dir))
  if(FLAGS.data_augment_options!='None'):
    options_augmented_str = FLAGS.data_augment_options
    options_augmented = list(options_augmented_str.split(" "))
    aug = ""
    
    for i in options_augmented:
      line = "data_augmentation_options{\n\t"+i+"{\n\t\t}\n  }"
      aug = aug+line
      
      #aug = "data_augmentation_options{\n\trandom_pixel_value_scale{\n\t\t}\n  }\n"

    with open(updated_pipeline_config_file, 'r+') as f: #r+ does the work of rw
      lines = f.readlines()
      for i, line in enumerate(lines):
          if line.strip().startswith('batch_size'):
              lines[i] = lines[i].strip() + '\n'+aug+'\n'
      f.seek(0)
      for line in lines:
          f.write(line)
        
  return updated_pipeline_config, updated_pipeline_config_file


def train_model(pipeline_config_file):
  checkpoint_dir = os.path.join(FLAGS.output_dir.replace("\\", '/').replace("//", ''), 'checkpoints')
  if (os.path.exists(checkpoint_dir)): 
    shutil.rmtree(checkpoint_dir) # only use models trained in this call
  param2 = '--train_dir=' + checkpoint_dir
  param3 = '--pipeline_config_path=' + pipeline_config_file
  param1 = '--logtostderr'
  logger.info('current directory: {}'.format(os.getcwd()))
  model_main = 'tftrain.py'
  logger.info('calling {} {} {}'.format(model_main, param1, param2, param3))
  # raise exception if call to the main training code failes
  subprocess.check_call([sys.executable, model_main, param1, param2, param3]) 
  checkpoint_prefix = os.path.join(checkpoint_dir, 'model.ckpt-' + str(FLAGS.num_steps))
  logger.info('checkpoint_prefix: {}'.format(checkpoint_prefix))
  return checkpoint_prefix

def export_model(pipeline_config, checkpoint_prefix):
  export_dir = os.path.join(FLAGS.output_dir, 'model')
  if (os.path.exists(export_dir)): #there's no overwrite option for exporting
    shutil.rmtree(export_dir)

  exporter.export_inference_graph(
    'image_tensor', 
    pipeline_config, 
    str(checkpoint_prefix).replace("\\", '/'),
    str(export_dir).replace("\\", '/'))


def main():
  global logger
  os.makedirs(FLAGS.log_dir.replace("\\", '/').replace("//", ''), exist_ok=True)
  os.makedirs(FLAGS.output_dir.replace("\\", '/').replace("//", ''), exist_ok=True)
  logconf = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'logging.yml')
  print('logconf {}'.format(logconf))
  if os.path.exists(logconf):
    with open(logconf, 'rt') as f:
      config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)
    print('logconf loaded')
  else:
    logging.basicConfig(level=default_level) 
    print('logconf fall back to default')
  logger = logging.getLogger('train')

  pipeline_config, pipeline_config_file = update_pipeline_config()
  checkpoint_prefix = train_model(pipeline_config_file)
  export_model(pipeline_config, checkpoint_prefix)


if __name__ == '__main__':
  main()

