#!/usr/bin/env python3
"""
script to run the container with mounting for network, shared folder, etc
"""

from subprocess import PIPE, Popen, PIPE
import argparse
import shlex
import sys

class Vars:
    # script-wide variables
    container_runtime = "docker"
    container_base = "xa-scale-"
    container_image_base = f"svce-xa-scale:{container_base}"
    registry = "amr-idc-registry.infra-host.com"
    registry_folder = "asv-content"
    max_saved_container_retries = 10  # how many redundant containers we'll make e.g. container.1.tar, container.2.tar
    proj_root = "xa-scale" 

    # command-line informed variables
    rel_ver = 1.0
    extra_args = ""
    extra_start = -1
    tar_file_name = f"{container_base}{rel_ver}.tar"
    verbose = False

def arg_parsing():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--runtime", type=str, help="Container runtime built", default="")
   
    args = parser.parse_args()

    return args

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



def run():
    # run the container with the appropriate mounting
    tag = "TAG"
    id = "IMAGE"
    cmd_to_run_images = ["docker","run","--privileged","-it"]
    selected_option = -1
    snapshot_name = ""
   
    if Vars.container_runtime == "containerd":
        tag = "REF"
        id = "REF" # In this case container will run using the tag indicated by REF
        cmd_to_run_images = ["ctr","run","-rm","-t","--privileged"]
        snapshot_name = "xa-scale"

    past_images, table_header_row = search_past_images()
    if past_images:
        tag_index = table_header_row.index(f"{tag}")
        id_index = table_header_row.index(f"{id}")
        for number,line in enumerate(past_images):
            tokens_line = line.split()
            print(f"{number} {tokens_line[tag_index]}")
            
        if len(past_images) > 1:
            while True:
                try:
                    selected_option = int(input("Which container do you want to run? (Enter number)"))
                except ValueError:
                    print("Option must be a valid number!")
                else:
                    break
    
        try:       
            selected_line = past_images[selected_option]
            selected_line_tokens = selected_line.split()
            image_id = selected_line_tokens[id_index]
            image_tag = selected_line_tokens[tag_index]
            cmd = cmd_to_run_images + [image_id] + [snapshot_name]
            print(f"Running {image_tag} {image_id} image")
            print(f"Command line: {cmd}")
            out, err, code = run_command(cmd)  
            if code == 0:
                print("Container ran succesfully!")   
        except IndexError:
            print(f"Invalid selected option {selected_option}")
            return
        
    return
    
def main():
    
    args = arg_parsing()
    if args.runtime != "":
        Vars.container_runtime = args.runtime
    run()


if __name__ == "__main__":
    main()

# make sure to handle parameters for the container