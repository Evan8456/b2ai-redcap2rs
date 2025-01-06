import requests
import json

import os
import argparse
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
import pandas as pd

def to_bids(survey_data, record_id, session_path, columns):
    session_id = session_path.split("/")[0]
    questionnaire_name = survey_data[0]["used"][1].split("/")[-1]
    questions_answers = dict()
    questions_answers["record_id"] = [record_id]
    questions_answers["redcap_repeat_instrument"] = [questionnaire_name]
    questions_answers["redcap_repeat_instance"] = [1]
    start_time = survey_data[0]["startedAtTime"]
    end_time = survey_data[0]["endedAtTime"]
    for i in range(len(survey_data)):
        if i % 2 == 1:  # odd index contains the answer
            question = survey_data[i]["isAbout"].split("/")[-1]
            answer = survey_data[i]["value"]
            if not isinstance(answer, list):
                questions_answers[question] = [str(answer).capitalize()]
                columns[question] = [str(answer).capitalize()]
                
            else:
                num = fetch_json_options_number(survey_data[i]["isAbout"])
                redcap_columns = columns.copy()
                # eg. replace race with race___1 ... race___n
                new_columns = {}
                for questions in columns:
                    if questions == question:
                        redcap_columns.pop(question)
                        break
                    new_columns[questions] = columns[questions]
                    redcap_columns.pop(questions)

                for options in range(num):
                    if options in answer:
                        questions_answers[f"""{question}___{options}"""] = [
                            "Checked"]
                        new_columns[f"""{question}___{options}"""] = [
                            "Checked"]
                    else:
                        questions_answers[f"""{question}___{options}"""] = [
                            "Unchecked"]
                        new_columns[f"""{question}___{options}"""] = [
                            "Unchecked"]

                columns = {**new_columns, **redcap_columns}
        else:
            end_time =  survey_data[i]["endedAtTime"]
    # Adding metadata values for redcap
    questions_answers[f"{questionnaire_name}_start_time"] = [start_time]
    questions_answers[f"{questionnaire_name}_end_time"] = [end_time]

    columns[f"{questionnaire_name}_start_time"] = [start_time]
    columns[f"{questionnaire_name}_end_time"] = [end_time]
    duration =  calculate_duration(start_time, end_time)
    questions_answers[f"{questionnaire_name}_duration"] = [duration]
    columns[f"{questionnaire_name}_duration"] = [duration]
    
    questions_answers[f"{questionnaire_name}_sessionId"] = [session_id]
    columns[f"{questionnaire_name}_sessionId"] = [session_id]
    
    df = pd.DataFrame(questions_answers)
    directory_path = f"""Combined_Data3/sub-{record_id}/{session_id}01/beh"""
    os.makedirs(directory_path, exist_ok=True)
    filename = f"""{questionnaire_name}.csv"""
    file_path = os.path.join(directory_path, filename)
    df.to_csv(file_path, index=False)

    return columns


def load_json_files(directory):
    json_data = []

    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
                json_data += data

    return dict.fromkeys(json_data)


def calculate_duration(start_time, end_time):
    # Convert the time strings to datetime objects with UTC format
    time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    start = datetime.strptime(start_time, time_format)
    end = datetime.strptime(end_time, time_format)
    
    # Calculate the difference between the two times
    duration = end - start
    
    # Get the duration in milliseconds
    milliseconds = duration.microseconds // 1000
    
    return milliseconds


def fetch_json_options_number(raw_url):
    try:
        # fix url due to the split
        
        raw_url = raw_url.replace("combined", "questionnaires")
        # Make a GET request to the raw URL
        response = requests.get(raw_url, verify=True)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)

        # Parse the JSON data
        json_data = response.json()
        return len(json_data["responseOptions"]["choices"])

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return
    except ValueError:
        print("Error parsing JSON data")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # string param of path to folder containing reproschema files
    parser.add_argument("survey_file",
                        type=str,
                        help="path to folder containing survey files")

    args = parser.parse_args()

    # Probably use b2aiprep for this down the road
    directory_path = './instrument_columns/'
    loaded_columns = load_json_files(directory_path)

    folder = Path(args.survey_file)
    if not os.path.isdir(folder):
        raise FileNotFoundError(
            f"{folder} does not exist. Please check if folder exists and is located at the correct directory"
        )

    # load each file recursively within the folder into its own key
    content = OrderedDict()
    for file in folder.glob("**/*"):
        if file.is_file():
            # get the full path to the file *after* the base folder path
            # since files can be referenced by relative paths, we need to keep track of relative location
            filename = str(file.relative_to(folder))
            with open(f"{folder}/{filename}") as f:
                content[filename] = json.loads(f.read())

    record_id = args.survey_file.split("/")[-1]
    for questionnaire in content.keys():
        loaded_columns = to_bids(content[questionnaire], (args.survey_file.split(
            "/")[-1]).split()[0], questionnaire, loaded_columns)

    df = pd.DataFrame(loaded_columns)
    directory_path = "Combined_Data3"
    os.makedirs(directory_path, exist_ok=True)
    filename = f"""{record_id}_combined.csv"""
    file_path = os.path.join(directory_path, filename)
    df.to_csv(file_path, index=False)
