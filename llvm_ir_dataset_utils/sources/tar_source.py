"""Module that downloads and extracts tar archives."""

import os
import tarfile
import tempfile
import shutil
from urllib import request


def download_source_code(archive_url, base_dir, source_folder_name):
  try:
    with tempfile.TemporaryDirectory() as download_dir:
      file_download_path = os.path.join(download_dir,
                                        'tar-source-download.tar.gz')
      request.urlretrieve(archive_url, file_download_path)
      with tarfile.open(file_download_path) as source_tar_archive:
        source_tar_archive.extractall(download_dir)
      os.remove(file_download_path)
      real_source_folder_name = os.path.join(download_dir,
                                            os.listdir(download_dir)[0])
      shutil.move(real_source_folder_name,
                  os.path.join(base_dir, source_folder_name))
    return True
  except:
    return False