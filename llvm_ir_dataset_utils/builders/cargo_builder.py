"""Module for building and extracting bitcode from applications using cargo"""

import subprocess
import os
import json
import multiprocessing
import shutil

from absl import logging

import ray

from compiler_opt.tools import make_corpus_lib


def get_spec_from_id(id):
  # We're taking in a string like
  # my-package 0.1.0 (path+file:///path/to/my-package) and we want to be  able
  # to get file:///path/to/my-package from it, so we perform the following
  # process:
  # 1. .split('(') - Split at the first parenthese to get rid of the space
  #    separated package and id.
  # 2. [1] - Get the section after the split that we want.
  # 3. [5:-1] - Remove the parenthese at the end and the path+ section at
  #    the beginning of the post split string.
  return id.split('(')[1][5:-1]

def get_packages_from_manifest(source_dir):
  command_vector = ["cargo", "metadata", "--no-deps"]
  try:
    # TODO(boomanaiden154): Dump the stderr of the metadata command to a log
    # somewhere
    with subprocess.Popen(
        command_vector,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=source_dir) as process:
      out, err = process.communicate()
      manifest = json.loads(out.decode("utf-8"))
    packages = {}
    for package in manifest["packages"]:
      targets = []
      for target in package["targets"]:
        targets.append({
            "name": target["name"],
            "kind": target["kind"][0],
            "spec": get_spec_from_id(package['id']),
            "package": package['name']
        })
      packages[package["name"]] = targets
    return packages
  except:
    return []


def get_build_log_path(corpus_dir, target):
  return os.path.join(corpus_dir,
                      target['name'] + '.' + target['kind'] + '.build.log')


def build_all_targets(source_dir, build_dir, corpus_dir, threads,
                      extra_env_variables, cleanup):
  package_list = get_packages_from_manifest(source_dir)
  build_log = {'targets': []}
  package_futures = []
  for package in package_list:
    package_build_dir = build_dir + '-' + package
    package_futures.append(
        build_package_future(source_dir, package_build_dir, corpus_dir,
                             package_list[package], threads,
                             extra_env_variables, cleanup))
  package_build_logs = ray.get(package_futures)
  for package_build_log in package_build_logs:
    build_log['targets'].extend(package_build_log)
  return build_log


def build_package_future(source_dir, build_dir, corpus_dir, targets, threads,
                         extra_env_variables, cleanup):
  return build_package.options(num_cpus=threads).remote(source_dir, build_dir,
                                                        corpus_dir, targets,
                                                        threads,
                                                        extra_env_variables,
                                                        cleanup)


@ray.remote(num_cpus=multiprocessing.cpu_count())
def build_package(source_dir, build_dir, corpus_dir, targets, threads,
                  extra_env_variables, cleanup):
  build_log = []
  for target in targets:
    build_log.append(
        perform_build(source_dir, build_dir, corpus_dir, target, threads,
                      extra_env_variables))
  extract_ir(build_dir, corpus_dir)
  if cleanup:
    if os.path.exists(build_dir):
      shutil.rmtree(build_dir)
  return build_log


def perform_build(source_dir, build_dir, corpus_dir, target, threads,
                  extra_env_variables):
  logging.info(
      f"Building target {target['name']} of type {target['kind']} from package {target['package']}"
  )
  build_env = os.environ.copy()
  build_env["CARGO_TARGET_DIR"] = build_dir
  build_env.update(extra_env_variables)
  build_command_vector = [
      "cargo", "rustc", "-p", f"{target['spec']}", "-j",
      str(threads)
  ]
  if target['kind'] == "lib":
    build_command_vector.append("--lib")
  elif target['kind'] == "test":
    build_command_vector.extend(["--test", target['name']])
  elif target['kind'] == "bench":
    build_command_vector.extend(["--bench", target['name']])
  elif target['kind'] == "bin":
    build_command_vector.extend(["--bin", target['name']])
  elif target['kind'] == "example":
    build_command_vector.extend(["--example", target['name']])
  else:
    logging.warn("Unrecognized target type, not building.")
    return False
  build_command_vector.extend(["--", '--emit=llvm-bc'])
  try:
    with open(get_build_log_path(corpus_dir, target), 'w') as build_log_file:
      subprocess.run(
          build_command_vector,
          cwd=source_dir,
          env=build_env,
          check=True,
          stdout=build_log_file,
          stderr=build_log_file)
  except:
    logging.warn(
        f"Failed to build target {target['name']} of type {target['kind']} from package {target['package']}"
    )
    build_success = False
  logging.info(
      f"Finished building target {target['name']} of type {target['kind']} from package {target['package']}"
  )
  build_success = True
  return {
      'success': build_success,
      'build_log': get_build_log_path(corpus_dir, target),
      'name': target['name'] + '.' + target['kind']
  }


def extract_ir(build_dir, corpus_dir):
  # TODO(boomanaiden154): Look into getting a build manifest from cargo.
  relative_paths = make_corpus_lib.load_bitcode_from_directory(build_dir)
  make_corpus_lib.copy_bitcode(relative_paths, build_dir, corpus_dir)
  make_corpus_lib.write_corpus_manifest(relative_paths, corpus_dir, '')
