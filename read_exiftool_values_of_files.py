import os
import sys
from logging import DEBUG, INFO, basicConfig, getLogger
from pathlib import Path
from typing import Final

import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict, Field, NewPath, NonNegativeFloat, StrictStr

from extract_image_taken_datetime import (
    EncodingStr,
    ExifTool,
    InputConfig,
    PathEncodingConverterMixin,
)


class ProcessConfig(BaseModel):
    """Processing section of the configuration.
    'PROCESS' in YAML.

    Attributes:
        EXIFTOOL_PROGRESS_PRINT_PERIOD_SECONDS (optional):
            Interval for printing ExifTool progress. Defaults to Inf (no printing).
        TARGET_EXIFTOOL_TAGS (optional):
            ExifTool tags to show value in output CSV. [specific tags mode]
            If not be set, all tags are shown, but the value will be masked. [all tags mode]
    """

    EXIFTOOL_PROGRESS_PRINT_PERIOD_SECONDS: NonNegativeFloat = float('inf')
    TARGET_EXIFTOOL_TAGS: list[StrictStr] = []

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class FilePathsListWithExifToolTagsCsvConfig(PathEncodingConverterMixin, BaseModel):
    """Configuration for output CSV containing file paths and extracted ExifTool tags.
    'OUTPUT' > 'FILE_PATHS_LIST_WITH_EXIFTOOL_TAGS_CSV' in YAML.

    Attributes:
        PATH: Path to a new output CSV file.
        ENCODING: Encoding to use when writing the CSV.
        VALUE_MASKING_STRING (optional):
            Masking string in all tags mode (1 length at least). Default to "●".
        ORIGINAL_COLUMNS_SUFFIX (optional):
            Suffix string to original columns duplicated with ExifTool tags (1 length at least).
            Default to "_ORG".
    """

    PATH: NewPath  # Must not exist & parent must exist
    ENCODING: EncodingStr
    VALUE_MASKING_STRING: StrictStr = Field('●', min_length=1)
    ORIGINAL_COLUMNS_SUFFIX: StrictStr = Field('_ORG', min_length=1)

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

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
        FILE_PATHS_LIST_WITH_EXIFTOOL_TAGS_CSV: Configuration for the output CSV file.
    """

    FILE_PATHS_LIST_WITH_EXIFTOOL_TAGS_CSV: FilePathsListWithExifToolTagsCsvConfig

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


def get_all_exiftool_tags():

    basicConfig(level=INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    logger = getLogger(__name__)

    logger.info(f'"{os.path.basename(__file__)}" start!')

    if not ExifTool.is_installed():
        logger.critical('"exiftool" is necessary, but not installed on this pc.')
        logger.critical('See https://exiftool.org/index.html.')
        sys.exit(1)

    CONFIG: Final[Config] = __read_arg_config_path()

    if len(CONFIG.PROCESS.TARGET_EXIFTOOL_TAGS) == 0:
        logger.info('Running in "all tags mode".: Masking all values.')
    else:
        logger.info('Running in "specific tags mode".: Showing all values.')

    source_csv_config = CONFIG.INPUT.FILE_PATHS_LIST_CSV
    source_csv_df = source_csv_config.read_csv()
    if source_csv_df.shape[0] == 0:
        logger.error(f'No lines in the csv "{source_csv_config.PATH}".')
        sys.exit(1)

    processing_df = source_csv_df.copy()

    logger.info('Scanning profiles of the files...')
    path_str_list = processing_df[source_csv_config.FILE_PATHS_LIST_COLUMN].tolist()
    with ExifTool(tuple(CONFIG.PROCESS.TARGET_EXIFTOOL_TAGS)) as _exiftool:
        exiftool_result_list = _exiftool.execute_on_files(
            path_str_list,
            CONFIG.PROCESS.EXIFTOOL_PROGRESS_PRINT_PERIOD_SECONDS,
        )

    output_csv_config = CONFIG.OUTPUT.FILE_PATHS_LIST_WITH_EXIFTOOL_TAGS_CSV
    if len(CONFIG.PROCESS.TARGET_EXIFTOOL_TAGS) == 0:
        # all tags mode
        exiftool_tags_values_list = [
            (
                {key: output_csv_config.VALUE_MASKING_STRING for key in each_dict.keys()}
                if each_dict is not None
                else {}
            )
            for each_dict in exiftool_result_list
        ]
    else:
        # specific tags mode
        exiftool_tags_values_list = [
            (each_dict if each_dict is not None else {}) for each_dict in exiftool_result_list
        ]

    logger.info('Merging profiles data to source CSV data...')
    exiftool_tags_values_df = pd.DataFrame(exiftool_tags_values_list, index=processing_df.index)

    exiftool_tags_count_series = exiftool_tags_values_df.notna().sum()
    all_columns_in_frequency_order = exiftool_tags_count_series.sort_values(
        ascending=False
    ).index.to_list()
    exiftool_tags_values_df = exiftool_tags_values_df[all_columns_in_frequency_order]

    processing_df = processing_df.join(
        exiftool_tags_values_df, lsuffix=output_csv_config.ORIGINAL_COLUMNS_SUFFIX
    )

    output_csv_config.write_csv_from_dataframe(processing_df, index=False)

    logger.info(f'"{os.path.basename(__file__)}" done!')


if __name__ == '__main__':
    get_all_exiftool_tags()
