#!/bin/python
"""This script wraps the compiler, taking in the compiler options and saving
the source files that are used within the compilation step."""

import os
import subprocess
import sys
import shutil

RECOGNIZED_SOURCE_FILE_EXTENSIONS = ['.c', 'cpp', '.cxx', '.cc']


def run_compiler_invocation(mode, compiler_arguments):
  command_vector = []

  if mode == 'c++':
    command_vector.append('clang++')
  else:
    command_vector.append('clang')

  command_vector.extend(compiler_arguments)

  subprocess.run(command_vector)


def save_preprocessed_source(mode, compiler_arguments, source_file_stem):
  # We shouldn't fail to find the output here if the argument parsing
  # succeeded.
  output_index = compiler_arguments.index('-o') + 1
  arguments_copy = compiler_arguments.copy()
  output_path = arguments_copy[
      output_index] + f'.{source_file_stem}.preprocessed_source'
  arguments_copy[output_index] = output_path

  # Add -E to the compiler invocation to run just the preprocessor.
  arguments_copy.append('-E')

  run_compiler_invocation(mode, arguments_copy)


def save_source(source_files, output_file, mode, compiler_arguments):
  for source_file in source_files:
    current_file_stem = os.path.basename(source_file).split('.')[0]
    new_file_name = output_file + f'.{current_file_stem}.source'
    shutil.copy(source_file, new_file_name)

    save_preprocessed_source(mode, compiler_arguments, current_file_stem)


def parse_args(arguments_split):
  output_file_path = None
  try:
    output_arg_index = arguments_split.index('-o') + 1
    output_file_path = arguments_split[output_arg_index]
  except:
    return None

  input_files = []

  for argument in arguments_split:
    for recognized_extension in RECOGNIZED_SOURCE_FILE_EXTENSIONS:
      if argument.endswith(recognized_extension):
        input_files.append(argument)

  mode = 'c++'
  if not arguments_split[0].endswith('++'):
    mode = 'c'

  return (output_file_path, input_files, mode)


def main(args):
  parsed_arguments = parse_args(args)
  if not parsed_arguments:
    # We couldn't parse the arguments. This could be for a varietey of reasons.
    # In this case, don't copy over any files and just run the compiler
    # invocation.
    run_compiler_invocation(args[1:])

  output_file_path, input_files, mode = parsed_arguments

  save_source(input_files, output_file_path, mode, args[1:])

  run_compiler_invocation(mode, args[1:])


if __name__ == '__main__':
  main(sys.argv)
