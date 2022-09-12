#!/usr/bin/env python3
import os
import requests
import sys
import base64
import json
import time
import datetime
import xml.etree.ElementTree as ET
from lxml import etree
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


def init_vars():
    # initialize the environmental variables for this session
    jss = os.environ.get("JSS")
    api_user = os.environ.get("JSSUSER")
    api_pw = os.environ.get("JSSPASS")
    server_type = os.environ.get("SERVERTYPE")
    home = str(Path.home())
    if server_type == "windows":
        tmp_path = f"{home}\\JamfAPISync\\"
        log_folder_path = f"{tmp_path}\\Logs\\"
    else:
        tmp_path = f"{home}/JamfAPISync/"
        log_folder_path = f"{tmp_path}/Logs/"
    debug_mode_tf = True
    return jss, api_user, api_pw, tmp_path, log_folder_path, debug_mode_tf


def insert_into_xml(filename, application_name, mobile_device_identifier,
                    mobile_device_application_status, mobile_device_id, mobile_device_application_short_version):
    """ Takes the parsed app and device info and inserts into output XML"""
    tree = ET.ElementTree(file=filename)
    root = tree.getroot()
    found = False

    for element in root.findall("mobile_device_application"):
        # Check if bundle ID exists already in XML file
        if mobile_device_identifier in element.find("bundle_id").text:
            found = True
            break

    if found:
        # updating existing application information
        # mda = element
        for devices_element in element.findall("devices"):
            device = ET.SubElement(devices_element, "device")
            did = ET.SubElement(device, "id")
            did.text = mobile_device_id
            mdasv = ET.SubElement(device, "application_version")
            mdasv.text = mobile_device_application_short_version
            mdas = ET.SubElement(device, "application_status")
            mdas.text = mobile_device_application_status
            tree = ET.ElementTree(root)
            tree.write(filename)
            break
    else:
        # use bundle ID from list created earlier to confirm app identity and assign correct app ID
        index = -1
        app_record_found = False
        for app_bundle_id in app_bundle_ids:
            index += 1
            if app_bundle_id == mobile_device_identifier:
                app_record_found = True
                break

        if app_record_found:
            mobile_app_id = str(app_ids[index])
            if application_name == "NAME NOT FOUND":
                # name for this app not found in device record, defaulting to primary app list
                application_name = str(app_names[index])
            # adding new application information
            mda = ET.SubElement(root, "mobile_device_application")
            mdaid = ET.SubElement(mda, "application_id")
            mdaid.text = mobile_app_id
            an = ET.SubElement(mda, "application_name")
            an.text = application_name
            bid = ET.SubElement(mda, "bundle_id")
            bid.text = mobile_device_identifier
            devices = ET.SubElement(mda, "devices")
            device = ET.SubElement(devices, "device")
            did = ET.SubElement(device, "id")
            did.text = mobile_device_id
            mdasv = ET.SubElement(device, "application_version")
            mdasv.text = mobile_device_application_short_version
            mdas = ET.SubElement(device, "application_status")
            mdas.text = mobile_device_application_status
            tree = ET.ElementTree(root)
            tree.write(filename)
        else:
            write_to_logfile(
                f"INFO: App found in Mobile Device record but no Jamf object to reference. Not adding to XML: {application_name, mobile_device_identifier}",
                now_formatted, "std")


def generate_xml(filename):
    # creates the initial XML structure before inserting values
    root = ET.Element("mobile_device_applications")
    m1 = ET.Element("mobile_device_application")
    root.append(m1)

    b1 = ET.SubElement(m1, "id")
    b1.text = " "
    b2 = ET.SubElement(m1, "application_name")
    b2.text = " "
    b3 = ET.SubElement(m1, "bundle_id")
    b3.text = " "
    b4 = ET.SubElement(m1, "internal_app")
    b4.text = " "

    m2 = ET.Element("devices")
    m1.append(m2)
    m3 = ET.Element("device")
    m2.append(m3)
    c1 = ET.SubElement(m3, "id")
    c1.text = " "
    c2 = ET.SubElement(m3, "application_version")
    c2.text = " "
    c3 = ET.SubElement(m3, "application_status")
    c3.text = " "

    tree = ET.ElementTree(root)

    with open(filename, "wb") as file:
        tree.write(file)
    pretty(tmp_path + f"mobile_applications_{now_formatted}.xml")


def pretty(filename):
    f = etree.parse(filename)
    content = etree.tostring(f, pretty_print=True, encoding=str)
    # print(content)
    return content


def remove_empty_xml_tags(filename):
    # removes the empty tags in XML file we used for template structure
    with open(filename, 'r+', encoding='utf-8') as fp:
        # read and store all lines into list
        lines = fp.readlines()
        # move file pointer to the beginning of a file
        fp.seek(0)
        # truncate the file
        fp.truncate()
        # start writing lines
        # iterate line and line number
        for number, line in enumerate(lines):
            # delete line number 5 and 8
            # note: list index start from 0
            if number not in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]:
                fp.write(line)


def generate_auth_token():
    # generate api token
    global api_token_valid_start_epoch

    credentials = api_user + ":" + api_pw
    credentials_bytes = credentials.encode('ascii')
    base64_bytes = base64.b64encode(credentials_bytes)
    encoded_credentials = base64_bytes.decode('ascii')
    # api call details
    jss_token_url = jss + "/api/v1/auth/token"
    payload = {}

    headers = {
        'Authorization': 'Basic ' + encoded_credentials
    }

    response = requests.request("POST", jss_token_url, headers=headers, data=payload)
    check_response_code(str(response), jss_token_url)
    # parse the json from the request
    response_data_dict = json.loads(response.text)
    # assign variable as global to be used in other functions
    api_token = response_data_dict['token']
    # Token is valid for 30 minutes. Setting timestamp to check for renewal
    api_token_valid_start_epoch = int(time.time())

    return api_token


def check_token_expiration_time():
    """api_token_valid_start_epoch is created globally when token is generated and api_token_valid_check_epoch is created locally to generate
    api_token_valid_duration_seconds which determines how long the token has been active"""
    api_token_valid_check_epoch = int(time.time())
    api_token_valid_duration_seconds = api_token_valid_check_epoch - api_token_valid_start_epoch
    # Renew token if necessary
    if api_token_valid_duration_seconds >= 1500:
        write_to_logfile(
            f"UPDATE: API auth token is {api_token_valid_duration_seconds} seconds old. Token will now be renewed to continue API access.....",
            now_formatted, "std")
        generate_auth_token()


def check_response_code(response_code: str, api_call: str):
    response_code = str(response_code)
    response_code = response_code[11:14]
    if response_code != "200" and response_code != "201":
        write_to_logfile(f"ERROR: response returned for {api_call} [{response_code}]", now_formatted, "std")
        print(f"ERROR: response returned [{response_code}]")
        print(response_code)
        sys.exit(1)
    else:
        write_to_logfile(f"INFO: http response for {api_call} [{response_code}]", now_formatted, "debug")


def get_all_ids(device_type, filename):
    page_size = 100
    page = 0

    def refresh_api_url():
        if device_type == 'computers':
            api_url = jss + f"/api/v1/computers-inventory?section=GENERAL&page={page}&page-size={page_size}&sort=id%3Aasc"
        elif device_type == 'mobiledevices':
            api_url = jss + f"/api/v2/mobile-devices?page={page}&page-size={page_size}&sort=id%3Aasc"
        return api_url

    api_url = refresh_api_url()

    payload = {}
    headers = {
        'Authorization': 'Bearer ' + api_token
    }

    check_token_expiration_time()
    response = requests.request("GET", api_url, headers=headers, data=payload)
    check_response_code(str(response), api_url)
    reply = response.text  # just the json, to save to file
    # write JSON to /tmp/jss_temp.....
    print(reply, file=open(tmp_path + filename, "w+", encoding='utf-8'))  # writes output to /tmp

    all_ids_json_filepath = open(tmp_path + filename, encoding='utf-8')
    all_ids_json_data = json.load(all_ids_json_filepath)

    total_id_count = all_ids_json_data['totalCount']
    write_to_logfile(f"INFO: {device_type} found in Jamfcloud [{total_id_count}]", now_formatted, "std")

    # loop through JSON results in order to create list of all IDs
    all_ids = []
    # append all IDs to variables established above
    count_on_page = page_size
    # adjust variable if total is less than page size. This avoids creating "list index out of range" error when looping through IDs
    if total_id_count < count_on_page:
        count_on_page = total_id_count

    id_index = 0
    while id_index < count_on_page:
        next_id = all_ids_json_data['results'][id_index]['id']
        all_ids.append(next_id)
        id_index += 1

    all_ids_count = len(all_ids)
    write_to_logfile(f"INFO: IDs retrieved [{all_ids_count} of {total_id_count}].....", now_formatted, "std")

    while all_ids_count < total_id_count:
        page += 1
        api_url = refresh_api_url()
        check_token_expiration_time()
        response = requests.request("GET", api_url, headers=headers, data=payload)
        check_response_code(str(response), api_url)
        reply = response.text
        # write JSON to /tmp/jss_temp.....
        print(reply, file=open(tmp_path + filename, "w+", encoding='utf-8'))

        all_ids_json_filepath = open(tmp_path + filename, encoding='utf-8')
        all_ids_json_data = json.load(all_ids_json_filepath)

        id_index = 0
        should_keep_tabulating = True
        while should_keep_tabulating:
            if all_ids_count < total_id_count and id_index < count_on_page:
                next_id = all_ids_json_data['results'][id_index]['id']
                all_ids.append(next_id)
                id_index += 1
                # refresh count of IDs
                all_ids_count = len(all_ids)
            else:
                should_keep_tabulating = False

        write_to_logfile(f"INFO: IDs retrieved [{all_ids_count} of {total_id_count}].....", now_formatted, "std")
    all_ids_json_filepath.close()
    os.remove(tmp_path + filename)
    return all_ids


def parse_mobile_device_info():
    # loop through the IDs we gathered in previous step
    for id in all_ids:
        write_to_logfile(f"INFO: parsing mobile device with id: {id}", now_formatted, "debug")
        # make api call to retrieve inventory for each computer
        # use subset/Applications to only return the list of applications by mobile device ID
        api_url = f"{jss}/JSSResource/mobiledevices/id/{id}/subset/Applications"
        tmp_file = f"{tmp_path}_mobileDeviceID_{id}.xml"
        payload = {}
        headers = {
            'Accept': 'application/xml',
            'Authorization': 'Bearer ' + api_token
        }

        check_token_expiration_time()
        response = requests.request("GET", api_url, headers=headers, data=payload)
        check_response_code(str(response), api_url)
        reply = response.text  # just the xml, to save to file
        # write XML to /tmp folder
        print(reply, file=open(tmp_file, "w+", encoding='utf-8'))
        # parse all computer info
        tree = ET.parse(tmp_file)
        root = tree.getroot()

        mobile_device_id = id
        # mobile_device_application_name = " "
        # mobile_device_application_short_version = " "
        # mobile_device_application_status = " "
        # mobile_device_identifier = " "
        for a in root.findall('.//application'):
            mobile_device_application_name = getattr(a.find('application_name'), 'text', None)
            if not mobile_device_application_name:
                write_to_logfile(
                    f"ERROR: xml parse of mobile device ID {id} returned NONE for name. Assigning [NAME NOT FOUND]",
                    now_formatted, "std")
                mobile_device_application_name = "NAME NOT FOUND"
            # mobile_device_application_name = mobile_device_application_name.replace("'", r"\'")
            mobile_device_identifier = getattr(a.find('identifier'), 'text', None)
            mobile_device_application_status = getattr(a.find('application_status'), 'text', None)
            mobile_device_application_short_version = getattr(a.find('application_short_version'), 'text', None)
            # append values to XML output
            insert_into_xml(
                tmp_path + f"mobile_applications_{now_formatted}.xml", mobile_device_application_name,
                mobile_device_identifier, mobile_device_application_status, mobile_device_id, mobile_device_application_short_version
            )
        os.remove(tmp_file)


def gather_application_ids():
    # gather all application IDs and assign as key pairs with application name
    write_to_logfile(f"INFO: gathering all application IDs and names", now_formatted, "debug")
    # make api call to retrieve inventory for each computer
    # use subset/Applications to only return the list of applications by mobile device ID
    api_url = f"{jss}/JSSResource/mobiledeviceapplications"
    tmp_file = f"{tmp_path}allMobileDeviceApplications.json"
    payload = {}
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + api_token
    }

    check_token_expiration_time()
    response = requests.request("GET", api_url, headers=headers, data=payload)
    check_response_code(str(response), api_url)
    reply = response.text  # just the xml, to save to file
    # write JSON to /tmp folder
    print(reply, file=open(tmp_file, "w+", encoding='utf-8'))
    # parse all mobile application info
    all_app_ids_json_filepath = open(tmp_file, encoding='utf-8')
    all_app_ids_json_data = json.load(all_app_ids_json_filepath)
    app_ids = []
    app_names = []
    app_display_names = []
    app_bundle_ids = []
    index = 0
    for element in all_app_ids_json_data['mobile_device_applications']:
        app_ids.append(f"unknownID_{index}") if element["id"] is None else app_ids.append(element["id"])
        app_names.append(f"unknownName_{index}") if element["name"] is None else app_names.append(element["name"])
        # app_display_names.append(f"unknownDisplayName_{index}") if element["display_name"] is None else app_display_names.append(element["display_name"])
        app_bundle_ids.append(f"unknownBundleID_{index}") if element["bundle_id"] is None else app_bundle_ids.append(element["bundle_id"])
        index += 1

    all_app_ids_json_filepath.close()
    os.remove(tmp_file)
    return app_ids, app_names, app_bundle_ids


def write_to_logfile(log_to_print, timestamp, debug_or_std):
    # create file if it doesn't exist. the "w+ option overwrites existing file content.
    if debug_or_std == "std":
        print(log_to_print, file=open(log_folder_path + "/JamfAPISync-" + timestamp + ".log", "a+", encoding='utf-8'))
    elif debug_or_std == "debug" and debug_mode_tf:
        # only print debug logs if debug_mode_tf is true
        print(f"DEBUG: {log_to_print}", file=open(log_folder_path + "/JamfAPISync-" + timestamp + ".log", "a+", encoding='utf-8'))


def now_date_time():
    now = str(datetime.datetime.now())
    # splits string into a list with 2 entries
    now = now.split(".", 1)
    # assign index 0 of the new list (as a string) to now
    now_formatted = str(now[0])

    char_to_replace = {':': '', ' ': '-'}
    # Iterate over all key-value pairs in dictionary
    for key, value in char_to_replace.items():
        # Replace key character with value character in string
        now_formatted = now_formatted.replace(key, value)

    return now_formatted


def script_duration(start_or_stop):
    # this function calculates script duration
    days = 0; hours = 0; mins = 0; secs = 0
    global start_script_epoch

    if start_or_stop == "start":
        print("[SCRIPT START]")
        start_script_epoch = int(time.time())  # converting to int for simplicity
    else:
        stop_script_epoch = int(time.time())
        script_duration_in_seconds = stop_script_epoch - start_script_epoch

        if script_duration_in_seconds > 59:
            secs = int(script_duration_in_seconds % 60)
            script_duration_in_seconds = int(script_duration_in_seconds / 60)

            if script_duration_in_seconds > 59:
                mins = int(script_duration_in_seconds % 60)
                script_duration_in_seconds = script_duration_in_seconds / 60

                if script_duration_in_seconds > 23:
                    hours = int(script_duration_in_seconds % 24)
                    days = int(script_duration_in_seconds / 24)
                else:
                    hours = int(script_duration_in_seconds)
            else:
                mins = int(script_duration_in_seconds)
        else:
            secs = int(script_duration_in_seconds)

        write_to_logfile(f"\n\n\n---------------\nSUCCESS: script completed.  XML file can be found in {tmp_path}", now_formatted, "std")
        write_to_logfile(f"SCRIPT DURATION: {days} day(s) {hours} hour(s) {mins} minute(s) {secs} second(s)", now_formatted,
                         "std")
        print("[SCRIPT COMPLETE!]")


def create_script_directory(days_ago_to_delete_logs):
    # Check whether the specified path exists or not
    path_exists = os.path.exists(log_folder_path)

    if not path_exists:
        # Create a new directory because it does not exist
        os.makedirs(log_folder_path)
        write_to_logfile(f"CREATE: new directory {log_folder_path} created!", now_formatted, "debug")
    else:
        write_to_logfile(f"INFO: the directory {log_folder_path} already exists", now_formatted, "debug")

        x_days_ago = time.time() - (days_ago_to_delete_logs * 86400)
        write_to_logfile(f"DELETE: deleting log files older than {days_ago_to_delete_logs} days", now_formatted, "debug")

        for i in os.listdir(log_folder_path):
            path = os.path.join(log_folder_path, i)

            if os.stat(path).st_mtime <= x_days_ago and os.path.isfile(path):
                os.remove(path)
                write_to_logfile(f"DELETE: [{path}]", now_formatted, "std")


if __name__ == "__main__":
    script_duration("start")
    now_formatted = now_date_time()
    jss, api_user, api_pw, tmp_path, log_folder_path, debug_mode_tf = init_vars()
    create_script_directory(14)
    api_token = generate_auth_token()
    """app bundle id is gathered in individual mobile device record.  
    Record details in XML we're creating are confirmed using app_bundle_ids 
    in order to match up ID with app name"""
    app_ids, app_names, app_bundle_ids = gather_application_ids()
    all_ids = get_all_ids("mobiledevices", "all_mobile_devices.json")
    # create blank XML structure
    generate_xml(tmp_path + f"mobile_applications_{now_formatted}.xml")
    parse_mobile_device_info()
    # pretty the XML by copying, cleaning and pasting into document
    pretty_xml = pretty(tmp_path + f"mobile_applications_{now_formatted}.xml")
    with open(tmp_path + f"mobile_applications_{now_formatted}.xml", "w", encoding='utf-8') as file:
        file.write(pretty_xml)

    remove_empty_xml_tags(tmp_path + f"mobile_applications_{now_formatted}.xml")
    script_duration("stop")
