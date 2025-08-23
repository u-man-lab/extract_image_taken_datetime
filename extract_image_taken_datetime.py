import codecs
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zoneinfo
from logging import DEBUG, INFO, basicConfig, getLogger
from pathlib import Path
from typing import Any, ClassVar, Final

import dateutil
import pandas as pd
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    FilePath,
    NewPath,
    NonNegativeFloat,
    StrictStr,
    field_validator,
)


class EncodingStr:
    """Represents a validated string that must be a valid text encoding name.

    Validates whether the provided string is a supported encoding.
    """

    def __init__(self, value: Any):
        self.__validate_value(value)
        self.__value: str = value

    def __str__(self) -> str:
        return self.__value

    @staticmethod
    def __validate_value(arg: Any) -> str:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')

        try:
            codecs.lookup(arg)
        except LookupError as err:
            raise ValueError(f'"{arg}" is not supported as an encoding string.') from err
        return arg


class PathEncodingConverterMixin:
    """Pydantic mixin for automatic validation and conversion of PATH and ENCODING fields.

    Provides field validators for converting string paths to 'Path' and encoding strings
    to 'EncodingStr' during model initialization.
    """

    @field_validator('PATH', mode='before')
    @classmethod
    def __convert_str_to_file_path_and_validate(cls, arg: Any) -> Path:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return Path(arg.strip())

    @field_validator('ENCODING', mode='before')
    @classmethod
    def __convert_str_to_encoding_str_and_validate(cls, arg: Any) -> EncodingStr:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return EncodingStr(arg.strip())


class FilePathsListCsvConfig(PathEncodingConverterMixin, BaseModel):
    """Configuration for a CSV file containing a list of file paths.
    'INPUT' > 'FILE_PATHS_LIST_CSV' in YAML

    Attributes:
        PATH: Path to an existing CSV file.
        ENCODING: Encoding used to read the CSV.
        FILE_PATHS_LIST_COLUMN: Column name containing file paths.
    """

    PATH: FilePath  # Must be existing file
    ENCODING: EncodingStr
    FILE_PATHS_LIST_COLUMN: StrictStr

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

    def __get_missing_columns(self, df: pd.DataFrame) -> tuple[str, ...]:
        """Returns a tuple of necessary columns that does not exist in the given DataFrame.

        Args:
            df: DataFrame to check columns missing.

        Returns:
            tuple[str, ...]: A tuple of necessary columns that does not exist in the df.
        """

        NECESSARY_COLUMNS: Final[tuple[str, ...]] = (self.FILE_PATHS_LIST_COLUMN,)

        return tuple(col for col in NECESSARY_COLUMNS if col not in df.columns)

    def read_csv(self, allow_empty: bool = True) -> pd.DataFrame:
        """Reads the configured CSV file into a pandas DataFrame.

        Args:
            allow_empty: Whether to allow empty rows below header row.

        Returns:
            pd.DataFrame: DataFrame containing the contents of the CSV file.
        """

        getLogger(__name__).info(f'Reading CSV file "{self.PATH}"...')

        df = pd.read_csv(self.PATH, encoding=str(self.ENCODING), dtype=str, keep_default_na=False)

        missing_columns = self.__get_missing_columns(df)
        if missing_columns:
            missing_columns_str = '", "'.join(missing_columns)
            raise ValueError(f'Necessary columns are missing in the CSV.: "{missing_columns_str}"')

        if not allow_empty and df.shape[0] == 0:
            raise ValueError('Empty rows in the CSV.')

        return df


class InputConfig(BaseModel):
    """Input section of the configuration.
    'INPUT' in YAML.

    Attributes:
        FILE_PATHS_LIST_CSV: Configuration for the input file list CSV.
    """

    FILE_PATHS_LIST_CSV: FilePathsListCsvConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class ProcessConfig(BaseModel):
    """Processing section of the configuration.
    'PROCESS' in YAML.

    Attributes:
        DEFAULT_TIMEZONE_FOR_NAIVE_DATETIME_VALUE:
            Timezone to apply if a datetime string is without timezone (naive).
        EXIFTOOL_PROGRESS_PRINT_PERIOD_SECONDS (optional):
            Interval seconds for printing ExifTool progress. Defaults to Inf (no printing).
        EXIFTOOL_TAGS_OF_IMAGE_TAKEN_DATETIME_IN_PRIORITY_ORDER:
            Priority-ordered ExifTool tags to extract image datetime.
    """

    DEFAULT_TIMEZONE_FOR_NAIVE_DATETIME_VALUE: zoneinfo.ZoneInfo
    EXIFTOOL_PROGRESS_PRINT_PERIOD_SECONDS: NonNegativeFloat = float('inf')
    EXIFTOOL_TAGS_OF_IMAGE_TAKEN_DATETIME_IN_PRIORITY_ORDER: list[StrictStr]

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

    @field_validator('DEFAULT_TIMEZONE_FOR_NAIVE_DATETIME_VALUE', mode='before')
    @classmethod
    def __convert_str_to_tzinfo(cls, arg: Any) -> zoneinfo.ZoneInfo:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        try:
            timezone = zoneinfo.ZoneInfo(arg)
        except zoneinfo.ZoneInfoNotFoundError as err:
            raise ValueError(
                f'"{arg}" is not supported as "DEFAULT_TIMEZONE_FOR_NAIVE_DATETIME_VALUE".'
            ) from err
        return timezone


class FilePathsListWithImageTakenDatetimeCsvConfig(PathEncodingConverterMixin, BaseModel):
    """Configuration for output CSV containing file paths and extracted image datetime data.
    'OUTPUT' > 'FILE_PATHS_LIST_WITH_IMAGE_TAKEN_DATETIME_CSV' in YAML.

    Attributes:
        PATH: Path to a new output CSV file.
        ENCODING: Encoding to use when writing the CSV.
        LOCAL_TIMEZONE_FOR_UNIX_TIMESTAMP: Timezone for "DATETIME_LOCAL_UNIX_COLUMN" below.
        DATETIME_TAG_BY_EXIFTOOL_COLUMN: Column name for detected ExifTool tag.
        DATETIME_BY_EXIFTOOL_COLUMN: Column name for raw string value of ExifTool tag.
        DATETIME_AWARE_ISO8601_EXTENDED_COLUMN: Column name for ISO 8601 formatted datetime.
        DATETIME_LOCAL_UNIX_COLUMN: Column name for UNIX-format-localized timestamp.
    """

    PATH: NewPath  # Must not exist & parent must exist
    ENCODING: EncodingStr
    LOCAL_TIMEZONE_FOR_UNIX_TIMESTAMP: zoneinfo.ZoneInfo
    DATETIME_TAG_BY_EXIFTOOL_COLUMN: StrictStr
    DATETIME_BY_EXIFTOOL_COLUMN: StrictStr
    DATETIME_AWARE_ISO8601_EXTENDED_COLUMN: StrictStr
    DATETIME_LOCAL_UNIX_COLUMN: StrictStr

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

    @field_validator('LOCAL_TIMEZONE_FOR_UNIX_TIMESTAMP', mode='before')
    @classmethod
    def __convert_str_to_tzinfo(cls, arg: Any) -> zoneinfo.ZoneInfo:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        try:
            timezone = zoneinfo.ZoneInfo(arg)
        except zoneinfo.ZoneInfoNotFoundError as err:
            raise ValueError(
                f'"{arg}" is not supported as "LOCAL_TIMEZONE_FOR_UNIX_TIMESTAMP".'
            ) from err
        return timezone

    def get_already_existing_new_columns(self, df: pd.DataFrame) -> tuple[str, ...]:
        """Returns a tuple of columns that already exist in the given DataFrame
        and would conflict with newly added datetime columns.

        Args:
            df: DataFrame to check for column name conflicts.

        Returns:
            tuple[str, ...]: Existing column names in the df.
        """

        NEW_COLUMNS: Final[tuple[str, ...]] = (
            self.DATETIME_TAG_BY_EXIFTOOL_COLUMN,
            self.DATETIME_BY_EXIFTOOL_COLUMN,
            self.DATETIME_AWARE_ISO8601_EXTENDED_COLUMN,
            self.DATETIME_LOCAL_UNIX_COLUMN,
        )

        return tuple(col for col in NEW_COLUMNS if col in df.columns)

    def write_csv_from_dataframe(
        self, df: pd.DataFrame, columns: list | None = None, index: bool = True
    ):
        """Writes the given DataFrame to the configured output CSV file.

        Args:
            df: DataFrame to write.
            columns (optional): Specific columns to include. Writes all if None.
            index (optional): Whether to include the DataFrame index. Defaults to True.
        """

        getLogger(__name__).info(f'Writing CSV file "{self.PATH}"...')
        df.to_csv(self.PATH, encoding=str(self.ENCODING), columns=columns, index=index)


class OutputConfig(BaseModel):
    """Output section of the configuration.
    'OUTPUT' in YAML.

    Attributes:
        FILE_PATHS_LIST_WITH_IMAGE_TAKEN_DATETIME_CSV: Configuration for the output CSV file.
    """

    FILE_PATHS_LIST_WITH_IMAGE_TAKEN_DATETIME_CSV: FilePathsListWithImageTakenDatetimeCsvConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class Config(BaseModel):
    """Main configuration object loaded from YAML.

    Attributes:
        INPUT: Input file configuration.
        PROCESS: Processing parameters configuration.
        OUTPUT: Output file configuration.
    """

    INPUT: InputConfig
    PROCESS: ProcessConfig
    OUTPUT: OutputConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    @classmethod
    def from_yaml(cls, path: str | Path) -> 'Config':
        """Loads the configuration from a YAML file.

        Args:
            path: Path to the YAML config file.

        Returns:
            Config: Parsed configuration object.
        """

        with open(path, 'r', encoding='utf-8') as fr:
            content = yaml.safe_load(fr)
        return cls(**content)


def __read_arg_config_path() -> Config:
    """Parses the configuration file path from command-line arguments and loads the config.

    Returns:
        Config: Loaded configuration object.

    Raises:
        SystemExit: If the config path is not provided or cannot be parsed.
    """

    logger = getLogger(__name__)

    if len(sys.argv) != 2:
        logger.error('This script needs a config file path as an arg.')
        sys.exit(1)
    config_path = Path(sys.argv[1])

    try:
        CONFIG: Final[Config] = Config.from_yaml(config_path)
    except Exception:
        logger.exception(f'Failed to parse the config file.: "{config_path}"')
        sys.exit(1)

    return CONFIG


class ExifTool:
    """Context manager and interface for interacting with the external "exiftool" process.

    Supports persistent execution for performance and JSON output parsing.
    """

    __command_path = shutil.which('exiftool')
    __logger = getLogger(__name__)
    # stay stdin open & json output & tags with group & don't omit same name tags
    __STAY_OPEN_OPTIONS_LIST = ['-stay_open', 'True', '-@', '-', '-common_args', '-j', '-G', '-a']

    __process: subprocess.Popen

    @classmethod
    def is_installed(cls) -> bool:
        """Checks whether "exiftool" is installed and accessible in PATH.

        Returns:
            bool: True if installed, False otherwise.
        """

        return bool(cls.__command_path)

    def __init__(self, target_tags: tuple[str, ...] = tuple()):

        if not self.__class__.is_installed():
            raise RuntimeError('"exiftool" should be installed for this class.')

        if not isinstance(target_tags, tuple) or not all(
            isinstance(tag, str) for tag in target_tags
        ):
            raise TypeError(f'The argument must be a tuple of strs, got {type(target_tags)} type.')

        self.__target_tags = target_tags
        self.__process = None

    def __enter__(self) -> 'ExifTool':

        if self.__process is not None:
            raise RuntimeError('ExifTool context already entered.')

        subprocess_popen_args = [self.__command_path] + self.__STAY_OPEN_OPTIONS_LIST
        if self.__target_tags:
            subprocess_popen_args += [f'-{tag}' for tag in self.__target_tags]

        self.__process = subprocess.Popen(
            subprocess_popen_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        return self

    def __exit__(self, exc_type, exc_value, traceback):

        if self.__process is None:
            return

        # Try to close exiftool
        if self.__process.stdin:
            try:
                self.__process.stdin.write('-stay_open\nFalse\n')
                self.__process.stdin.flush()
            except Exception:
                self.__logger.warning('Failed to close exiftool.')

        # Try to close stdin, stdout, stderr
        for stream in (self.__process.stdin, self.__process.stdout, self.__process.stderr):
            if stream is None:
                continue
            try:
                stream.close()
            except Exception:
                self.__logger.warning('Failed to close stdin, stdout and stderr.')

        # Try to close process
        try:
            self.__process.terminate()
            self.__process.wait()
        except Exception:
            self.__logger.warning('Failed to close process.')

    def execute_on_files(
        self,
        file_paths_list: list[str],
        progress_print_period_sec: float,
    ) -> list[dict[str, str] | None]:
        """Executes "exiftool" on a list of file paths and returns parsed JSON metadata.

        Args:
            file_paths_list: List of file paths to process.
            progress_print_period_sec: Interval seconds for progress logging.

        Returns:
            list[dict[str, str] | None]:
                List of metadata dictionaries (or None if file missing)
                in the order of input file_paths_list.
        """

        if self.__process is None:
            raise RuntimeError('This method must be called within a "with" block.')
        if not self.__process.stdin or not self.__process.stdout:
            raise IOError('No connection to stdin or stdout.')

        if not file_paths_list:
            return []

        exists_list = list(map(os.path.exists, file_paths_list))
        existing_paths: list[str] = []
        for file_path, _exists in zip(file_paths_list, exists_list):
            if _exists:
                existing_paths.append(file_path)
            else:
                self.__logger.warning(f'File not found.: "{file_path}"')

        if not existing_paths:
            raise FileNotFoundError('All file paths do not exist.')

        self.__process.stdin.write('\n'.join(existing_paths) + '\n')
        self.__process.stdin.write('-execute\n')
        self.__process.stdin.flush()

        existing_paths_len = len(existing_paths)
        do_print_progress = progress_print_period_sec != float('inf')
        if do_print_progress:
            self.__logger.info(f'ExifTool processing... [0/{existing_paths_len} valid files]')

        lines_list: list[str] = []
        files_processed = 0
        started_time = time.monotonic()
        target_seconds_elapsed = progress_print_period_sec
        while True:

            # NOTE: This "readline" may block process if ExifTool stops its output for some reason.
            line: str = self.__process.stdout.readline()
            if line == '':
                raise RuntimeError('ExifTool process terminated or stdout closed unexpectedly.')
            if line.strip() == '{ready}':  # when all have been processed
                break

            lines_list.append(line)
            files_processed += line.count('}')

            if do_print_progress and time.monotonic() >= started_time + target_seconds_elapsed:
                target_seconds_elapsed += progress_print_period_sec
                self.__logger.info(
                    f'ExifTool processing... [{files_processed}/{existing_paths_len} valid files]'
                )

        if do_print_progress:
            self.__logger.info(
                f'ExifTool processing has been completed. [{existing_paths_len}/{existing_paths_len} valid files]'
            )

        try:
            result_list: list[dict[str, str]] = json.loads(''.join(lines_list))
        except json.decoder.JSONDecodeError as err:
            raise RuntimeError('ExifTool outputs a broken JSON.') from err

        if self.__target_tags:
            got_tags_set: set[str] = set()
            for each_dict in result_list:
                got_tags_set |= each_dict.keys()
            for target_tag in self.__target_tags:
                if target_tag not in got_tags_set:
                    self.__logger.warning(
                        f'A target ExifTool tag was not found from input files.: "{target_tag}"'
                    )

        full_result_list = [result_list.pop(0) if _exists else None for _exists in exists_list]
        return full_result_list


class DatetimeKeyValue(BaseModel):
    """Represents a key-value pair for datetime extracted from metadata.

    Attributes:
        key: The metadata tag key.
        raw_value: The raw datetime string from metadata.
        datetime_value: The converted datetime object.
    """

    key: StrictStr | None
    raw_value: StrictStr | None
    datetime_value: datetime.datetime | None

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    __RE_EXIFDATE_FORMAT: ClassVar[re.Pattern] = re.compile(r'(\d{4}):(\d{2}):(\d{2})')

    @classmethod
    def get_datetime_value_by_key(
        cls,
        dict_list: list[dict[str, str] | None],
        target_key_list: list[str],
        default_timezone: zoneinfo.ZoneInfo,
    ) -> list['DatetimeKeyValue']:
        """Attempts to extract and parse datetime values for a list of target keys.

        Args:
            dict_list: List of metadata dictionaries.
            target_key_list: Priority-ordered list of tag keys to look for.
            default_timezone: Timezone to apply if a datetime string is without timezone (naive).

        Returns:
            list[DatetimeKeyValue]: List of parsed datetime entries, one per dict.
        """

        datetime_key_value_list: list[DatetimeKeyValue] = []
        for each_dict in dict_list:

            if each_dict is None:
                datetime_key_value_list.append(cls(key=None, raw_value=None, datetime_value=None))
                continue

            for target_key in target_key_list:

                raw_value = each_dict.get(target_key)
                if raw_value is None:
                    continue

                # replace YYYY:MM:DD to YYYY-MM-DD as parse preparation
                adjusted_value = cls.__RE_EXIFDATE_FORMAT.sub(r'\1-\2-\3', raw_value)

                try:
                    # try to parse datetime strings in various expression
                    dt = dateutil.parser.parse(adjusted_value)
                except dateutil.parser.ParserError:
                    continue

                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=default_timezone)

                datetime_key_value_list.append(
                    cls(key=target_key, raw_value=raw_value, datetime_value=dt)
                )
                break

            else:
                datetime_key_value_list.append(cls(key=None, raw_value=None, datetime_value=None))

        return datetime_key_value_list


def __extract_image_taken_datetime():

    basicConfig(level=INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    logger = getLogger(__name__)

    logger.info(f'"{os.path.basename(__file__)}" start!')

    if not ExifTool.is_installed():
        logger.critical('"exiftool" is necessary, but not installed on this pc.')
        logger.critical('See https://exiftool.org/index.html.')
        sys.exit(1)

    CONFIG: Final[Config] = __read_arg_config_path()

    source_csv_config = CONFIG.INPUT.FILE_PATHS_LIST_CSV
    try:
        source_csv_df = source_csv_config.read_csv(allow_empty=False)
    except Exception:
        logger.exception(f'Failed to read the CSV "{source_csv_config.PATH}".')
        sys.exit(1)

    output_csv_config = CONFIG.OUTPUT.FILE_PATHS_LIST_WITH_IMAGE_TAKEN_DATETIME_CSV
    already_existing_new_columns = output_csv_config.get_already_existing_new_columns(
        source_csv_df
    )
    if already_existing_new_columns:
        already_existing_new_columns_str = '", "'.join(already_existing_new_columns)
        logger.error(
            f'Tried to create new columns, but already exist in "{CONFIG.INPUT.FILE_PATHS_LIST_CSV.PATH}".'
            + f': "{already_existing_new_columns_str}"'
        )
        sys.exit(1)

    processing_df = source_csv_df.copy()

    path_str_list = processing_df[source_csv_config.FILE_PATHS_LIST_COLUMN].tolist()

    logger.info('Scanning profiles of the files...')
    try:
        with ExifTool(
            tuple(CONFIG.PROCESS.EXIFTOOL_TAGS_OF_IMAGE_TAKEN_DATETIME_IN_PRIORITY_ORDER)
        ) as _exiftool:
            exiftool_result_list = _exiftool.execute_on_files(
                path_str_list,
                CONFIG.PROCESS.EXIFTOOL_PROGRESS_PRINT_PERIOD_SECONDS,
            )
    except Exception:
        logger.exception('Failed to execute ExifTool on the files.')
        sys.exit(1)

    logger.info('Searching image taken datetime data...')
    try:
        datetime_original_list = DatetimeKeyValue.get_datetime_value_by_key(
            exiftool_result_list,
            CONFIG.PROCESS.EXIFTOOL_TAGS_OF_IMAGE_TAKEN_DATETIME_IN_PRIORITY_ORDER,
            CONFIG.PROCESS.DEFAULT_TIMEZONE_FOR_NAIVE_DATETIME_VALUE,
        )
    except Exception:
        logger.exception('Failed to get image taken datetime from ExifTool results.')
        sys.exit(1)

    logger.info('Adding new columns...')
    processing_df[output_csv_config.DATETIME_TAG_BY_EXIFTOOL_COLUMN] = pd.Series(
        [dtorg.key for dtorg in datetime_original_list], index=processing_df.index
    )
    processing_df[output_csv_config.DATETIME_BY_EXIFTOOL_COLUMN] = pd.Series(
        [dtorg.raw_value for dtorg in datetime_original_list], index=processing_df.index
    )

    try:
        datetime_original_iso8601_list = [
            (
                dtorg.datetime_value.isoformat(timespec='microseconds')
                if dtorg.datetime_value is not None
                else None
            )
            for dtorg in datetime_original_list
        ]
        processing_df[output_csv_config.DATETIME_AWARE_ISO8601_EXTENDED_COLUMN] = pd.Series(
            datetime_original_iso8601_list, index=processing_df.index
        )
    except Exception:
        logger.exception(
            f'Failed to add column "{output_csv_config.DATETIME_AWARE_ISO8601_EXTENDED_COLUMN}".'
        )
        sys.exit(1)

    try:
        datetime_original_local_obj_list = [
            (
                dtorg.datetime_value.astimezone(
                    output_csv_config.LOCAL_TIMEZONE_FOR_UNIX_TIMESTAMP
                ).replace(tzinfo=None)
                if dtorg.datetime_value is not None
                else None
            )
            for dtorg in datetime_original_list
        ]
        datetime_original_local_unix_list = [
            (
                f'{l_obj.replace(tzinfo=datetime.timezone.utc).timestamp():.6f}'
                if l_obj is not None
                else None
            )
            for l_obj in datetime_original_local_obj_list
        ]
        processing_df[output_csv_config.DATETIME_LOCAL_UNIX_COLUMN] = pd.Series(
            datetime_original_local_unix_list, index=processing_df.index
        )
    except Exception:
        logger.exception(f'Failed to add column "{output_csv_config.DATETIME_LOCAL_UNIX_COLUMN}".')
        sys.exit(1)

    try:
        output_csv_config.write_csv_from_dataframe(processing_df, index=False)
    except Exception:
        logger.exception(f'Failed to write the CSV "{output_csv_config.PATH}".')
        sys.exit(1)

    logger.info(f'"{os.path.basename(__file__)}" done!')


if __name__ == '__main__':
    __extract_image_taken_datetime()
