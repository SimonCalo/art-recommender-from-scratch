import random
import os
import json
import shutil
from PIL import Image
import imagehash


def generate_list_of_filenames(
    file_path: str,
    file_ending: str,
    randomise: bool = False
        ) -> list[str]:
    """
    Generate a list of filenames within the specified directory that have the specified file ending.

    Args:
        file_path (str): The path to the directory containing the files.
        file_ending (str): The file ending to filter files by (e.g., '.jpg', '.png').
        randomise (bool, optional): Whether to randomize the order of filenames. Defaults to False.

    Returns:
        list[str]: A list of filenames with the specified file ending.
    """
    files = [
        file_path + "/" + file for file in os.listdir(file_path) if file.endswith(file_ending)
        ]
    if randomise:
        random.shuffle(files)
    return files


def generate_dict_of_images_and_jsons(
    list_of_image_names: list[str],
    jsons_path: str,
) -> dict:
    """Generate a dictionary of images and their corresponding jsons as dictionaries.

    Args:
        list_of_image_names (list[str]): image filenames to include in this dictionary.
        jsons_path (str): path to the jsons.

    Returns:
        dict: The dictionary containing image files as keys and their json as value.
    """
    output_dict = {}
    for image_name in list_of_image_names:
        image_name_without_extension = os.path.splitext(os.path.basename(image_name))[0]
        json_filename = jsons_path + "/" + image_name_without_extension + ".json"
        with open(json_filename, 'r') as file:
            data_dict = json.load(file)

        output_dict[image_name] = data_dict

    return output_dict


def consolidate_files_in_one_folder(
    folder_path: str,
    list_of_folders_to_unify: list[str],
    starting_subfolders: list[str] = ["images", "jsons"],
    destination_subfolders: list[str] = ["images", "jsons"],
) -> None:
    """
    Unify files from multiple folders into one overall folder. Add a prefix to the final filename
    to determine the origin of the file.
    
    Args:
        folder_path (str): The path to the destination folder.
        list_of_folders_to_unify (list[str]): The list of folder paths to be unified into one
        overall folder.
        starting_subfolders (list[str]): The list of subfolders to migrate in the original folder.
                                         Defaults to ["images", "jsons"].
        destination_subfolders (list[str]): The list of subfolders to create in the new folder.
                                            Defaults to ["images", "jsons"].                                 
    """
    for subfolder in destination_subfolders:
        os.makedirs(os.path.join(folder_path, subfolder), exist_ok=True)

    for original_folder in list_of_folders_to_unify:
        for subfolder in starting_subfolders:
            source_folder = os.path.join(original_folder, subfolder)
            if not os.path.exists(source_folder):
                continue
            
            for filename in os.listdir(source_folder):
                source_path = os.path.join(source_folder, filename)
                if os.path.isfile(source_path):
                    destination_path = os.path.join(
                        folder_path, subfolder, f"{os.path.basename(original_folder)}_{filename}"
                        )
                    shutil.move(source_path, destination_path)


def remove_imgs_and_jsons_copies(
    image_directory: str = 'consolidated_data/images/',
    json_directory: str = 'consolidated_data/jsons/',
) -> None:
    """
    This function removes the possible copies of the same image (and corresponding json) that are
    found in the specified directory. It uses perceptual hashes. So far, this problem has been found
    only with images from the met museum.

    Args:
        image_directory (str): The path to the directory containing the images.
        json_directory (str): The path to the directory containing the json..

    """
    directory = image_directory
    image_files = [
        os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(
            ('.jpg', '.jpeg', '.png')
            )
        ]
    image_hashes = {}

    for image_path in image_files:
        with Image.open(image_path) as img:
            image_hash = imagehash.phash(img)
            image_hashes[image_path] = image_hash

    for i, img1_path in enumerate(image_files):
        for j in range(i + 1, len(image_files)):
            img2_path = image_files[j]
            if image_hashes[img1_path] == image_hashes[img2_path]:
                
                if os.path.exists(img2_path):
                    os.remove(img2_path) 
                
                json_file_name = os.path.basename(img2_path).rsplit('.', 1)[0] + '.json'
                json_file_path = os.path.join(json_directory, json_file_name)
                
                if os.path.exists(json_file_path):
                    os.remove(json_file_path)
                