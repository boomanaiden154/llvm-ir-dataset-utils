"""A tool for performing dimensionality reduction and visualizing the results."""

import logging
import os
import csv

import numpy
import pandas
import umap

from sklearn.preprocessing import StandardScaler

import plotly.express

from absl import app
from absl import flags

import sys

FLAGS = flags.FLAGS

flags.DEFINE_multi_string(
    'properties_file', None,
    'The path to a file containing a list of functions and their numerical properties.'
)
flags.DEFINE_multi_string(
    'bitcode_distribution_file', None,
    'The path to a file containing a list of functions and opcode counts.')
flags.DEFINE_string('output_file', None, 'The path to the output image.')

flags.mark_flag_as_required('properties_file')
flags.mark_flag_as_required('bitcode_distribution_file')
flags.mark_flag_as_required('output_file')


def load_function_properties(file_path):
  function_properties = {}
  with open(file_path) as properties_file:
    properties_reader = csv.DictReader(properties_file)
    for property_entry in properties_reader:
      function_name = property_entry['name']
      property_entry.pop('name')
      function_properties[function_name] = property_entry
  return function_properties


def get_opcode_set(bitcode_distribution_paths):
  opcode_set = set()
  for bitcode_distribution_path in bitcode_distribution_paths:
    with open(bitcode_distribution_path) as bitcode_dist_file:
      dist_reader = csv.DictReader(bitcode_dist_file)
      for dist_row in dist_reader:
        for opcode_name in dist_row:
          opcode_set.add(opcode_name)
        break
  return list(opcode_set)


def add_bitcode_distribution(file_path, function_properties):
  with open(file_path) as distribution_file:
    distribution_reader = csv.DictReader(distribution_file)
    for distribution_entry in distribution_reader:
      function_name = distribution_entry['name']
      distribution_entry.pop('name')
      function_properties[function_name].update(distribution_entry)


def convert_to_feature_vector(function_properties):
  function_features = []
  for function in function_properties:
    individual_function_features = []
    for function_property in function_properties[function]:
      individual_function_features.append(
          int(function_properties[function][function_property]))
    function_features.append(individual_function_features)
  return function_features


def main(_):
  function_properties = {}

  colors = []

  logging.info('Loading data')
  for properties_file in FLAGS.properties_file:
    language_name = os.path.basename(properties_file)[:-4]
    new_properties = load_function_properties(properties_file)
    function_properties.update(new_properties)
    new_colors = [language_name] * len(new_properties)
    colors.extend(new_colors)

  # TODO(boomanaiden154): Add in support for adding in opcodes here too.
  # This needs to account for variability in opcodes between languages
  # though. Some functions are already implemented above.
  #for distribution_file in FLAGS.bitcode_distribution_file:
  #  add_bitcode_distribution(distribution_file, function_properties)

  function_feature_vectors = convert_to_feature_vector(function_properties)

  function_feature_arrays = numpy.asarray(function_feature_vectors)

  logging.info('Performing dimensionality reduction')

  scaled_data = StandardScaler().fit_transform(function_feature_arrays)

  reducer = umap.UMAP(n_neighbors=100)

  embedded_features = reducer.fit_transform(scaled_data)

  data_frame = pandas.DataFrame(
      numpy.asarray(embedded_features), columns=['x', 'y'])

  data_frame.insert(2, "colors", colors)

  figure = plotly.express.scatter(data_frame, x='x', y='y', color='colors')

  figure.write_image(FLAGS.output_file)


if __name__ == '__main__':
  app.run(main)