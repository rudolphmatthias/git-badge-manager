import glob
import os
import shutil
import uuid
from enum import Enum, auto
from pathlib import Path
from typing import List, Union
import logging
import subprocess

from aws_cdk import (
    aws_lambda,
    core
)

from aws_cdk.aws_s3_assets import Asset

logger = logging.getLogger(__name__)

EXCLUDE_DEPENDENCIES = {"urllib3", "six", "s3transfer", "python-dateutil", "jmespath", "docutils", "botocore",
                        "boto3", "setuptools", "pip"}
EXCLUDE_FILES = {'*.dist-info', '__pycache__', '*.pyc', '*.pyo'}


class PythonAssetType(Enum):
    Layer = auto()
    Lambda = auto()


class PythonS3CodeAsset(aws_lambda.S3Code):
    def __init__(self, scope: core.Construct, id: str,
                 runtime: aws_lambda.Runtime,
                 work_dir: Union[str, Path],
                 sources: List[str] = "*",
                 asset_code_type: PythonAssetType = PythonAssetType.Lambda,
                 as_zip_file=True) -> None:
        asset = PythonS3Asset(id=id, scope=scope, runtime=runtime, work_dir=work_dir, sources=sources,
                              asset_code_type=asset_code_type, as_zip_file=as_zip_file)

        super().__init__(bucket=asset.bucket, key=asset.s3_object_key)


class PythonS3Asset(Asset):
    """
    EXCLUDE_DEPENDENCIES - List of libraries already included in the lambda runtime environment. No need to package these.
    EXCLUDE_FILES - List of files not required and therefore safe to be removed to save space.
    """

    def __init__(self, scope: core.Construct, id: str,
                 runtime: aws_lambda.Runtime,
                 work_dir: Union[str, Path],
                 sources: List[str] = "*",
                 asset_code_type: PythonAssetType = PythonAssetType.Lambda,
                 as_zip_file=True) -> None:

        # variables
        python_bin = runtime.to_string()

        # prepare path
        work_dir, requirements_txt, build_dir, package_dir, sources, out_dir, zip_file = \
            self.prepare_paths(work_dir=work_dir, sources=sources)

        # change path
        cwd = Path.cwd()
        os.chdir(work_dir.as_posix())

        # build requirements and src
        self.build(python_bin=python_bin, build_dir=build_dir, requirements_txt=requirements_txt, sources=sources)

        # package src
        _package = self.package(build_dir=build_dir,
                                package_dir=package_dir,
                                asset_code_type=asset_code_type,
                                out_dir=out_dir,
                                zip_file=zip_file,
                                as_zip_file=as_zip_file)

        # change back path
        os.chdir(cwd.as_posix())
        super().__init__(scope=scope, id=id, path=_package.as_posix())

    @staticmethod
    def prepare_paths(work_dir, sources):
        # cleanup
        shutil.rmtree(work_dir / Path('.build'), ignore_errors=True)

        # paths
        prefix = str(uuid.uuid4())[:8]
        work_dir = Path(work_dir).resolve()
        requirements_txt = work_dir / 'requirements.txt'
        build_dir = work_dir / Path('.build') / f'{prefix}_build'
        package_dir = work_dir / Path('.build') / f'{prefix}_package'
        sources = [Path(work_dir / include_path).resolve() for include_path in sources]
        out_dir = work_dir / Path('.build') / f'{prefix}_out'
        zip_file = work_dir / Path('.build') / f'{prefix}.zip'

        # create new folders
        build_dir.mkdir(parents=True, exist_ok=True)
        package_dir.mkdir(parents=True, exist_ok=True)

        # logger
        logger.debug(f'Working directory: {work_dir}')
        logger.debug(f'Build directory: {build_dir}')
        logger.debug(f'Requirements file: {requirements_txt}')

        return work_dir, requirements_txt, build_dir, package_dir, sources, out_dir, zip_file

    @staticmethod
    def build(python_bin, build_dir, requirements_txt, sources) -> None:
        if requirements_txt.exists():
            # build with pip
            logger.debug('Installing dependencies [running on Linux]...')
            subprocess.run([f"{python_bin} -m pip -q install "
                            f"--target {build_dir} "
                            f"--requirement {requirements_txt}"], shell=True, check=True)

        # remove lambda runtime packages
        logger.debug('Removing dependencies bundled in lambda runtime and caches:')
        for pattern in EXCLUDE_DEPENDENCIES.union(EXCLUDE_FILES):
            pattern = str(build_dir / '**' / pattern)
            logger.debug(f'    -  {pattern}')
            files = glob.glob(pattern, recursive=True)
            for file_path in files:
                try:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except OSError:
                    logger.debug(f'Error while deleting file: {file_path}')

        # Add includes
        for item in sources:
            item.resolve()
            logger.debug(f'    -  {item}')
            os.system(f'cp -R {item} {build_dir}')

    @staticmethod
    def package(build_dir, package_dir, asset_code_type, out_dir, zip_file, as_zip_file) -> Path:
        # create subfolder if layer
        if asset_code_type == PythonAssetType.Layer:
            mv_dir = (package_dir / 'python')
            mv_dir.mkdir(parents=True, exist_ok=True)
        else:
            mv_dir = package_dir

        # move to package_dir
        for item in build_dir.glob('*'):
            os.system(f'mv {item} {mv_dir}')

        # zip
        if as_zip_file:
            # zip lambda/layer
            logger.debug(f'Packaging application into {zip_file}')
            shutil.make_archive(zip_file.with_suffix(''), 'zip', root_dir=package_dir.as_posix(), verbose=True)

            _return = zip_file

        else:
            # create out_dir
            out_dir.mkdir(parents=True, exist_ok=True)

            # move to out_dir
            for item in package_dir.glob('*'):
                os.system(f'mv {item} {out_dir}')

            _return = out_dir

        # cleanup and return
        shutil.rmtree(build_dir)
        shutil.rmtree(package_dir)

        return _return
