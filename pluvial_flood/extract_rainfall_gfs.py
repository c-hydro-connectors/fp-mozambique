#!/usr/bin/python3

"""
mozambique opChain - pluvial flooding - extract maximum forecast

__date__ = '20230119'
__version__ = '1.0.0'
__author__ =
        'Andrea Libertino (andrea.libertino@cimafoundation.org',
        'Flavio Pignone (flavio.pignone@cimafoundation.org',
        'Alessandro Masoero (alessandro.masoero@cimafoundation.org'
__library__ = 'mozambique'

General command line:
python3 extract_rainfall_gfs.py -settings_file pemba.json

Version(s):
20230119 (1.0.0) --> Beta release
"""
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Complete library
import xarray as xr
import os, json, logging, time, datetime
from argparse import ArgumentParser
import pandas as pd
import numpy as np

# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Algorithm information
alg_name = 'FP-MOZAMBIQUE - EXTRACT RAINFALL FOR PLUVIAL FLOOD'
alg_version = '1.0.0'
alg_release = '2023-01-19'
# Algorithm parameter(s)
time_format = '%Y%m%d%H%M'
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Script Main
def main():
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Get algorithm settings
    alg_settings, alg_time = get_args()

    # Set algorithm settings
    data_settings = read_file_json(alg_settings)

    # Set algorithm logging
    os.makedirs(data_settings['data']['log']['folder'], exist_ok=True)
    set_logging(logger_file=os.path.join(data_settings['data']['log']['folder'], data_settings['data']['log']['filename']))
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Info algorithm
    logging.info(' ============================================================================ ')
    logging.info(' ==> ' + alg_name + ' (Version: ' + alg_version + ' Release_Date: ' + alg_release + ')')
    logging.info(' ==> START ... ')
    logging.info(' ')

    # Time algorithm information
    start_time = time.time()

    time_run = datetime.datetime.strptime(alg_time, '%Y-%m-%d %H:%M')

    dict_empty = data_settings['algorithm']['template']
    dict_filled = dict_empty.copy()

    for key in dict_empty.keys():
        dict_filled[key] = time_run.strftime(dict_empty[key])
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Load forecast
    logging.info(" --> Search forecast file")
    input_file = os.path.join(data_settings["data"]["forecast"]["folder"], data_settings["data"]["forecast"]["filename"]).format(**dict_filled)
    if not os.path.isfile(input_file):
        logging.error(" --> Forecast file not found at " + input_file)
        raise FileNotFoundError
    logging.info(" --> Forecast file found!")
    frc_file = xr.open_dataset(input_file)

    # Loop from 0 (the location), then 1 (ne) up to 8 (clockwise)
    keys_for_loop = [(0,0),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1),(0,1)]

    # Loop around locations and extract the series
    for location in data_settings["data"]["location"].keys():
        logging.info(" --> Extracting location " + location)
        dict_filled["location"] = location

        ancillary_fld = data_settings["data"]["ancillary"]["folder"].format(**dict_filled)
        ancillary_file = os.path.join(ancillary_fld, data_settings["data"]["ancillary"]["filename"]).format(**dict_filled)
        os.makedirs(ancillary_fld, exist_ok=True)

        for ref_no,op in enumerate(keys_for_loop):
            series = frc_file.sel(lon=data_settings["data"]["location"][location][0] + op[0] * data_settings["data"]["forecast"]["resolution"], lat=data_settings["data"]["location"][location][1] + op[1] * data_settings["data"]["forecast"]["resolution"], method='nearest')
            if ref_no == 0:
                output_df = pd.DataFrame(index = series.time.values, columns=np.arange(0,len(keys_for_loop)))
            output_df.loc[:,ref_no]=series[data_settings["data"]["forecast"]["varname"]].values
        output_df.to_csv(ancillary_file, header=None)

        for time_delta in data_settings["data"]["time_delta"]:
            logging.info(" --> Operate moving average for time delta " + str(time_delta))
            dict_filled["time_delta"] = str(time_delta)
            resampled_df = output_df.rolling(time_delta, min_periods=time_delta).sum().max()
            output_fld = data_settings["data"]["output"]["folder"].format(**dict_filled)
            output_file = os.path.join(output_fld, data_settings["data"]["output"]["filename"]).format(**dict_filled)
            os.makedirs(output_fld, exist_ok=True)
            resampled_df.to_csv(output_file, header=None)

    if data_settings["algorithm"]["flags"]["clean_ancillary"]:
        logging.info(" --> Clean ancillary folder")
        os.system("rm -r " + ancillary_fld)
    # -------------------------------------------------------------------------------------
    # Info algorithm
    time_elapsed = round(time.time() - start_time, 1)

    logging.info(' ')
    logging.info(' ==> ' + alg_name + ' (Version: ' + alg_version + ' Release_Date: ' + alg_release + ')')
    logging.info(' ==> TIME ELAPSED: ' + str(time_elapsed) + ' seconds')
    logging.info(' ==> ... END')
    logging.info(' ==> Bye, Bye')
    logging.info(' ============================================================================ ')
    # -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Method to read file json
def read_file_json(file_name):

    env_ws = {}
    for env_item, env_value in os.environ.items():
        env_ws[env_item] = env_value

    with open(file_name, "r") as file_handle:
        json_block = []
        for file_row in file_handle:

            for env_key, env_value in env_ws.items():
                env_tag = '$' + env_key
                if env_tag in file_row:
                    env_value = env_value.strip("'\\'")
                    file_row = file_row.replace(env_tag, env_value)
                    file_row = file_row.replace('//', '/')

            # Add the line to our JSON block
            json_block.append(file_row)

            # Check whether we closed our JSON block
            if file_row.startswith('}'):
                # Do something with the JSON dictionary
                json_dict = json.loads(''.join(json_block))
                # Start a new block
                json_block = []

    return json_dict
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Function for fill a dictionary of templates
def fill_template(downloader_settings,time_now):
    empty_template = downloader_settings["templates"]
    template_filled = {}
    for key in empty_template.keys():
        template_filled[key] = time_now.strftime(empty_template[key])
    template_filled["domain"] = downloader_settings["domain"]
    return template_filled
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Method to get script argument(s)
def get_args():
    parser_handle = ArgumentParser()
    parser_handle.add_argument('-settings_file', action="store", dest="alg_settings")
    parser_handle.add_argument('-time', action="store", dest="alg_time")
    parser_values = parser_handle.parse_args()

    if parser_values.alg_settings:
        alg_settings = parser_values.alg_settings
    else:
        alg_settings = 'configuration.json'

    if parser_values.alg_time:
        alg_time = parser_values.alg_time
    else:
        alg_time = None

    return alg_settings, alg_time
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Method to set logging information
def set_logging(logger_file='log.txt', logger_format=None):

    if logger_format is None:
        logger_format = '%(asctime)s %(name)-12s %(levelname)-8s ' \
                        '%(filename)s:[%(lineno)-6s - %(funcName)20s()] %(message)s'

    # Remove old logging file
    if os.path.exists(logger_file):
        os.remove(logger_file)

    # Set level of root debugger
    logging.root.setLevel(logging.INFO)

    # Open logging basic configuration
    logging.basicConfig(level=logging.INFO, format=logger_format, filename=logger_file, filemode='w')

    # Set logger handle
    logger_handle_1 = logging.FileHandler(logger_file, 'w')
    logger_handle_2 = logging.StreamHandler()
    # Set logger level
    logger_handle_1.setLevel(logging.INFO)
    logger_handle_2.setLevel(logging.INFO)
    # Set logger formatter
    logger_formatter = logging.Formatter(logger_format)
    logger_handle_1.setFormatter(logger_formatter)
    logger_handle_2.setFormatter(logger_formatter)

    # Add handle to logging
    logging.getLogger('').addHandler(logger_handle_1)
    logging.getLogger('').addHandler(logger_handle_2)

# -------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Call script from external library
if __name__ == "__main__":
    main()
# ----------------------------------------------------------------------------