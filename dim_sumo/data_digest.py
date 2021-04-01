import sys
import pandas as pd
import numpy as np
import re
import glob
import xml.etree.cElementTree as ET
from pymongo import MongoClient
from PIL import Image

# Given the output from AIM, in a pandas dataframe, add a new run of the simulation to the mongo database
def add_run_to_mongo(input):
    client = MongoClient()
    db = client.tesis_DIM
    # We read the paramenters of the simulation from the first row, will fail if empty
    row = input.iloc[0]
    sim = {
        "run" : row.run_name,
        "prob_1" : float(row.deceiving_level_1),
        "prob_3" : float(row.deceiving_level_3),
        "freq_1" : float(row.traffic_level_1),
        "freq_3" : float(row.traffic_level_3),
        "done" : True
    }
    result = db.sim.insert_one(sim)
    # Add the run id as a column in the dataset
    input["run_id"] = result.inserted_id
    # Rename and remove columns to match the defined mongo db collection
    input = input.rename(columns={ "id" : "vin", "isDeceiver" : "deceiver", "depart": "start_time", "arrival" : "end_time", "duration" : "delay" })
    input = input.drop(columns=["deceiving_level_1", "deceiving_level_3", "traffic_level_1", "traffic_level_3", "run_name"])
    # Transform key columns to numeric columns
    input[["start_time", "delay", "end_time"]] = input[["start_time", "delay", "end_time"]].apply(pd.to_numeric)
    # Finally save the entries
    db.sim_vehicles.insert_many(input.to_dict(orient="records"))

# Calculates the average travel time after grouping
def times_per_group(input, group_by):
    group = input.groupby(by=group_by)
    return group["travel_time"].agg([np.mean, np.size, np.min, np.max, np.std])

# Reads a CSV file and returns adataframe. Also includes the isDeceiver column if it 
# is not present in the original file
def read_input(input_file):
    # Read the DIM input (adapted from https://stackoverflow.com/a/28267291)    
    input = ET.parse(input_file).getroot()
    # Load the info for every vehicle in the file
    return pd.DataFrame(list(iter_read_input_helper(input)))

# Generate a dictionary for each element in the file yielding as we generate each one
def iter_read_input_helper(input):
    for tripinfo in  input.iter("tripinfo"):
        yield tripinfo.attrib.copy()

# Adds the traffic level and deceiving level to all rows in the data set
def extend_with_params(data_frame, traffic_level_1, traffic_level_3, deceiving_level_1, deceiving_level_3, run_name):
    data_frame["traffic_level_1"] = traffic_level_1
    data_frame["traffic_level_3"] = traffic_level_3
    data_frame["deceiving_level_1"] = deceiving_level_1
    data_frame["deceiving_level_3"] = deceiving_level_3
    data_frame["run_name"] = run_name
    data_frame["isDeceiver"] = data_frame["id"].str.contains("_dec")
    data_frame.loc[data_frame["departLane"] == "1i_0",  "movement"] = "W->E" 
    data_frame.loc[data_frame["departLane"] == "3i_0",  "movement"] = "N->S" 

# Reads a CSV file and returns adataframe adding the traffic level and deceiving level
# from the filename
def read_input_and_extend(input_file):
    input = read_input(input_file)
    params = re.search(r"(\d{4}-\d{2}-\d{2}.*)\\tripinfo__t_(.*)_(.*)__d_(.*)_(.*).xml", input_file)
    extend_with_params(input, params.group(3), params.group(2), params.group(5), params.group(4), params.group(1))
    return input

# Writes a dataframe to an output file
def write_output(data, output_file):
    data.to_csv(output_file, index=False)

# Given a list of 2 DCLname (Data Collection Line name) produce the direction of travel
# of the vehicle. If there are less thatn 2 entries "NA" is returned, if there are more
# only the first 2 are used
def movement_by_colection_lines(lines):
    if lines.shape[0] < 2:
        return "NA"
    lines = lines.iloc
    if "Entrance" in lines[0]:
        return describe_movement(lines[0], lines[1])
    return describe_movement(lines[1], lines[0])

# Given an entry and an exit DCLname produces a string with the travel direction
# eg: N->W means the vehicle came from a north bound lane and exited in a west bound lane
def describe_movement(entrance_line, exit_line):
    entrance_direction = entrance_line[0:1]
    exit_direction = exit_line[0:1]    
    return f"{entrance_direction}->{exit_direction}"

# Reads all the files that match the pattern and returns a dataframe with all their contens
def read_all_with_pattern(file_name_pattern):
    # Creates a dataframe reading all the dataframes from path and saving it as a new file
    # Adapted from https://stackoverflow.com/questions/20906474/import-multiple-csv-files-into-pandas-and-concatenate-into-one-dataframe
    filenames = glob.glob(file_name_pattern)
    generator = (read_input_and_extend(f) for f in filenames)
    dataframe = pd.concat(generator, ignore_index=True)
    return dataframe

# Reads all the files that match the pattern and sned them to a MongoDB instance
def send_all_to_mongo_with_pattern(file_name_pattern):
    # Creates a dataframe reading all the dataframes from path and saving it as a new file
    # Adapted from https://stackoverflow.com/questions/20906474/import-multiple-csv-files-into-pandas-and-concatenate-into-one-dataframe
    filenames = glob.glob(file_name_pattern)    
    generator = (read_input_and_extend(f) for f in filenames)
    for df in generator:
        add_run_to_mongo(df)

# Stiches a set of images into a single one side by side, adapted from = https://stackoverflow.com/questions/30227466/combine-several-images-horizontally-with-python
def stich_images_side_by_side(input_file_names, result_file_name):
    images = [Image.open(x) for x in input_file_names]
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    new_im = Image.new('RGB', (total_width, max_height))

    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset,0))
        x_offset += im.size[0]

    new_im.save(result_file_name)

# Digest the information, mostly a way to use the other commans on a single call
def digest(source_folder):
    send_all_to_mongo_with_pattern(source_folder + "tripinfo__t_*.xml")

# Stich some images from the results
def stich(prefix):
    base = prefix
    files = [base + "_" + x + ".png" for x in ["A", "B", "ALL"]]
    stich_images_side_by_side(files, base + ".png")

folder="data\\results\\2020-10-13\\"
#stich(folder + "\\all")
#stich(folder + "\\no")
digest(source_folder=folder)