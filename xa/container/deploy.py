#!/usr/bin/env python3
"""
This file contains the logic to deploy the container either locally or to the cloud
similar to netstress/content/source/container_utils.py
"""
from subprocess import PIPE, Popen, PIPE
import sys
import shlex
import os
import argparse

class Vars:
    # script-wide variables
    container_runtime = "docker"
    container_base = "xa-scale-"
    container_image_base = f"svce-xa-scale:{container_base}"
    registry = "amr-idc-registry.infra-host.com"
    registry_folder = "asv-content"
    max_saved_container_retries = 10  # how many redundant containers we'll make e.g. container.1.tar, container.2.tar
    proj_root = "xa-scale" 
    cache_file = os.path.join(proj_root, ".image_cache")

    # command-line informed variables
    rel_ver = 1.0
    extra_args = ""
    extra_start = -1
    tar_file_name = f"{container_base}{rel_ver}.tar"
    verbose = False
    custom_name = False

def arg_parsing():
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--build", action="store_true", help="Build container")
    parser.add_argument("-s", "--save", action="store_true", help="Save container in tar file")
    parser.add_argument("-l", "--load", action="store_true", help="Load container tar file")
    parser.add_argument("-p", "--pull", action="store_true", help="Pull container")
    parser.add_argument("-c", "--clear", action="store_true", help="Clear docker/ctr images")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose", default=False)
    parser.add_argument("-t","--tar_file", type=str, help="tar file name to be loaded", default="")
    parser.add_argument("-r", "--runtime", type=str, help="Container runtime built", default="")
    parser.add_argument("-n","--name",type=str, help="Container name. Follow the format <name-version>",default="")
    args = parser.parse_args()

    return args

def get_dir_path(dir_to_search):
    """
     Search directory and return its path. Directory will be search form bottom to top.
     Number of directories to go up will be indicated by depth

    """
    depth = 2
    for level in range(depth):
        dir_path, found_folder = search_folder(os.getcwd(),dir_to_search)
        if found_folder:
            break
        os.chdir("..")
    return dir_path

def search_folder(folder_path=".", folder=""):
    """
     Search a folder in subdirectories given a initial path
    """
    current_folder = os.path.split(folder_path)[1]
    if current_folder == folder:
        return folder_path, True
    else:
        tree = os.walk(folder_path)
        folder_found = False
        for count,(main_dir, subdirs, files) in enumerate(tree):
            if count!=0:
                folder_path, folder_found = search_folder(main_dir,folder)
                if folder_found:
                    break
        return folder_path, folder_found
           
def run_command(cmd):

    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    elif isinstance(cmd, list):
        pass
    else:
        print(f"Cmd '{cmd}' is the wrong format, it should be a string or list of strings")
    p = Popen(cmd, stderr=sys.stderr, stdout= PIPE, text=True)
    out, err = p.communicate()
    if Vars.verbose:
        print(out)
    return out, err, p.returncode

def search_past_images():
    """
    Search container images that were cretead before

    """

    searched_container_tag = f"{Vars.container_base}"
    container_tag = ""
    list_images_cmd = "docker images"
    header_tag = "TAG"
    container_list = []
    remove_header_row = "ID" # Extra header row when we do a split to the header line

    if Vars.container_runtime == "containerd":
        list_images_cmd = "ctr image ls"
        header_tag = "REF"
        remove_header_row = ""

    out, err, code = run_command(f"{list_images_cmd}")
    output_lines_list = out.split("\n")
    first_line = output_lines_list.pop(0)
    table_header_row = first_line.split()
    try:
        table_header_row.remove(remove_header_row)
    except ValueError as e:
        pass

    tag_index = table_header_row.index(f"{header_tag}")

    for line in output_lines_list:
        line_tokens = line.split()
        if line_tokens:
            container_tag = line_tokens[tag_index]
            if  searched_container_tag in container_tag:
                container_list.append(line)

    return container_list,table_header_row

def get_image_versions():

    versions_list = []
    past_images,header_row = search_past_images()
    if past_images:
        header_tag = "TAG"
        tag_index = header_row.index(header_tag)
        for line in past_images:
            tokens_lines = line.split()
            tag = tokens_lines[tag_index]
            tokens_tag = tag.split("-")
            version = tokens_tag[-1]
            versions_list.append(version)
        versions_list.sort()

    return versions_list

def validate_name(name=""):

    valid_name = False
    if name.find("-") != -1:
        name_tokens = name.split("-")
        version = name_tokens[-1]
        numbers = version.split(".")
        for number in numbers:
            if not number.isdigit():
                print(f"{version} shoud be numbers separated by '.' ")
                break
        valid_name = True
    else:
        print(f"{name} is not in the format <name-version>")

    return valid_name



def build():
    """
    Build the container
    """

    versions_list = get_image_versions()
    if versions_list and not Vars.custom_name:
        version = versions_list[-1]
        Vars.rel_ver = round(float(version[:3]) + 0.1,2)

    folder_path = get_dir_path(Vars.proj_root)
    build_context_path = os.path.split(folder_path)[0]
    dockerfile_path = os.path.join(folder_path,'container','dockerfile')
    to_build = f"{Vars.container_image_base}{Vars.rel_ver}"
    print(f"Bulding container {to_build}")
    out, err, status_code =  run_command(f"docker build {build_context_path} --file {dockerfile_path} -t {to_build}")
    if status_code == 0:
        print("Container built succesfully! ")

def push():
    """
    Push the container to the registry
    """
    to_push = f"{Vars.registry}/{Vars.registry_folder}/{Vars.container_image_base}{Vars.rel_ver}"
    print(f"Pushing image to repository location: {to_push}")
    out, err, code = run_command(f"docker login {Vars.registry} -u \"robotasv-content+gitlab\" -p \"oVofO9rj1lwflXyqIcaelobVLPaprC0h\"")
    out, err, code = run_command(f"docker tag {Vars.container_image_base}{Vars.rel_ver} {to_push}")
    out, err, code = run_command(f"docker push {to_push}")
    print(f"Pushed image to repository location: {to_push}")

def pull():
    """
    Pull the container from the registry
    """
    # docker image pull amr-idc-registry.infra-host.com/asv-content/svce-nst:nst-0.1.2

    to_pull = f"{Vars.registry}/{Vars.registry_folder}/{Vars.container_image_base}{Vars.rel_ver}"

    if Vars.container_runtime == "docker":
        out, err, code = run_command(f"docker image pull {to_pull}")
    elif Vars.container_runtime == "containerd":
        out, err, code = run_command(f"ctr image pull {to_pull}")

def save():
    """
    Save the container to a tar file
    """
    image_versions = get_image_versions()
    if image_versions and not Vars.custom_name:
        Vars.rel_ver = image_versions[-1] # Getting most recent image
    to_save = f"{Vars.container_base}{Vars.rel_ver}.tar"
    print(f"Saving image tar file: {to_save}")
    proj_dir = get_dir_path(Vars.proj_root)
    out_file = f"{proj_dir}/{to_save}"

    if os.path.exists(out_file):
        for i in range(1, Vars.max_saved_container_retries):
            out_file = f"{proj_dir}/{Vars.container_base}{Vars.rel_ver}.{i}.tar"
            if not os.path.exists(out_file):
                if os.path.exists(f"{proj_dir}/{Vars.container_base}{Vars.rel_ver}.{i+1}.tar"):
                    '''
                    it seems there's a gap in the number of containers in the folder
                    e.g. container #4 missing but containers 1,2,3,5,6,7 exist
                    continue will skip that gap and try to find the last possible container
                    '''
                    continue
                break
        if i == Vars.max_saved_container_retries-1:
            image_size = os.path.getsize(out_file)*pow(10,-9)
            print(f"You have saved too many containers. {image_size:.2f}GB*{Vars.max_saved_container_retries}={Vars.max_saved_container_retries*image_size:.2f}GB of space wasted. Delete the saved images before saving more")
            exit(1)
    if Vars.container_runtime == "docker":
        out, err, code = run_command(f"docker save {Vars.container_image_base}{Vars.rel_ver} -o {out_file}")
    elif Vars.container_runtime == "containerd":
        try:
            out, err, code = run_command(f"ctr image pull {Vars.registry}/{Vars.container_image_base}{Vars.rel_ver}")
        except FileNotFoundError:
            print(f"Couldn't find image in {Vars.registry}! Please update image in {Vars.registry} before trying again.")
            exit(1)
        out, err, code = run_command(f"ctr image export {out_file} {Vars.registry}/{Vars.container_image_base}{Vars.rel_ver}")

def load():
    """
    Load the container from a tar file
    """
    to_load = Vars.tar_file_name
    print(to_load)
    print(f"Loading image tar file: {to_load}")
    if os.path.exists(to_load):
        if Vars.container_runtime == "docker":
            out, err, code = run_command(f"docker load --input {to_load}")
        elif Vars.container_runtime == "containerd":
            out, err, code = run_command(f"ctr image import {to_load}")
        if code == 0:
            print("Loaded image successfully!")
        else:
            print(f"Failed to load image from tarball! Exit code: {code}")
    else:
        print("File not found! Please enter full path to the image tarball.")
        exit(1)

def clear():
    """
    Clear the containers from docker/ctr memory
    """
   
    containers_to_be_removed = []
    header_id = "IMAGE"
    cmd_to_rm_images = ["docker","image","rm","-f"]

    if Vars.container_runtime == "containerd":
        header_id = "REF" # In this case we are not going to use id to rm the image instead we use the tag
        cmd_to_rm_images = ["ctr","image","rm"]

    past_images, header_row = search_past_images()
   
    if past_images:
        id_index = header_row.index(header_id)
        for line in past_images:
            line_tokens = line.split()
            if line_tokens:
                containers_to_be_removed.append(line_tokens[id_index])

        cmd = cmd_to_rm_images + containers_to_be_removed
        print(f"Removing {containers_to_be_removed} images")
        out, err, code = run_command(cmd)  
        if code == 0:
            print("Container image removed succesfully!")   
           
def main():
    """
    Main function for container utility
    """
    # call the utils file to build, save, and push the container
    args = arg_parsing()
    Vars.verbose = args.verbose

    if args.runtime != "":
        Vars.container_runtime = args.runtime
    if args.name !="":
       if validate_name(args.name):
           Vars.rel_ver = args.name.split("-")[-1]
           Vars.container_base = args.name.replace(Vars.rel_ver,"")
           Vars.custom_name = True
           print(f"{Vars.container_base} {Vars.rel_ver}")
           
    if args.build:
        build()
    if args.save:
        save()
    if args.load:
        if args.tar_file != "":
            Vars.tar_file_name = args.tar_file
        load()
    if args.pull:
        pull()
    if args.clear:
        clear()
              
    # copy run_xa script too

if __name__ == "__main__":
    main()
