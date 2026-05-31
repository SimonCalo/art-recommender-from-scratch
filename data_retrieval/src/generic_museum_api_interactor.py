import os
import json
import requests
from PIL import Image
import imagehash
import io
from data_retrieval.config.apis_params_config import museums_details


class GenericMuseumApiInteractor():
    """Generic class to interact with museum APIs to retrieve and save data.
    This class collects the basic methods and attributes shared among all
    API interactors."""

    def __init__(self, museum_name: str) -> None:
        """Instantiate an object of the class and retrieve attributes
        from config file.

        Args:
            museum_name: The name of the museum we want to create an API interactor
                         for. See config file for more details.
        """
        self.museum_name: str = museum_name
        self.museum_config: dict = museums_details[self.museum_name]
        self.base_url: str = self.museum_config["base_url"]
        self.key: str | None = self.museum_config["key"]
        self.exceptions: dict = self.museum_config["exceptions"]
        self.requirements: dict = self.museum_config["requirements"]
        self.hashes: list = []

    def get_response_dict(self, url: str, n_trial: int = 0) -> dict:
        """Get the content of an API response in the form of a dictionary.
        This method ensures that the code will not get stuck in faulty API calls,
        and will timeout the call after 10 seconds.

        Args:
            url: The url from which we want to retrieve the json response.
            n_trial: The number of triies already done to reach the link.
            It is used to make successive calls to this function in case the function times out.
            Defaults to 0.

        Returns:
            The API response content in the form of a dictionary.
        """

        json_data = {}
        try:
            # include a timeout to avoid getting stuck on one request
            response = requests.get(url, timeout=10)
            # Check if the request was successful
            if response.status_code == 200:
                json_data: dict = response.json()
            else:
                print(f"Error: {response.status_code} - {response.text}")
        # if the request timed out, try again for a max. of 5 times
        except requests.Timeout:
            if n_trial < 5:
                print(f"Trial {n_trial} failed. Sending request again")
                self.get_response_dict(url=url, n_trial=n_trial+1)
            else:
                print("Unable to reach link")

        return json_data

    def extract_image_url(self, image_id: str) -> None:
        """Currently not in use.
        It could be used to generate the correct link for an image given the specific museum
        and the image_id. This link would be used for subsequent download.

        Args:
            image_id:The id of the image we want to generate the url for.
        """
        return

    def passes_requirements(self, artwork_dict: dict) -> bool:
        """Check whether an artwork passes a set of requirements based on its
        json file.

        Args:
            artwork_dict: The dictionary extracted from the artwork's json.

        Returns:
            Whether the artwork passes the requirements or not.
        """
        for requirement in self.requirements:
            if self.requirements[requirement] is None:
                if str(artwork_dict[requirement]).lower() == "none":
                    return True

        return False
    
    def is_exception(self, artwork_dict: dict) -> bool:
        """Check whether an artwork should be considered an exception based on its
        json file details.

        Args:
            artwork_dict: The json file related to this specific artwork in the form
                          of a dictionary.

        Returns:
            Whether the artwork is to be considered an exception or not.
        """
        # check all the possible exceptions
        for exception in self.exceptions:
            if exception not in artwork_dict.keys():
                return True
            if artwork_dict[exception] is None:
                return True
            if isinstance(artwork_dict[exception], str):
                if artwork_dict[exception].lower() in self.exceptions[exception]:
                    return True
            elif isinstance(artwork_dict[exception], bool):
                if artwork_dict[exception] == self.exceptions[exception]:
                    return True
            elif isinstance(artwork_dict[exception], (int, float)):
                if artwork_dict[exception] in self.exceptions[exception]:
                    return True

        return False

    def download_image(self, url: str, image_name: str, n_trial: int = 0) -> bool:
        """Retrieve and download an image in a specific folder and with the chosen name.

        Args:
            url: The url from which to retrieve the image.
            image_name: The name with which the image should be saved.
            n_trial: The number of tries already done to reach the link.
                     It is used to make successive calls to this function in case the function times out.
                     Defaults to 0.

        Returns:
            true if the image was downloaded.
        """

        try:
            response = requests.get(url, timeout=10)
            # Check if the request was successful
            if response.status_code == 200:
                # Get the content of the response
                image_data = response.content

                if ".jpg" in str(image_name):
                    image_name = image_name.rstrip(".jpg")
                img_data = Image.open(io.BytesIO(image_data))
                image_hash = imagehash.phash(img_data)
                if image_hash not in self.hashes:
                    self.hashes.append(image_hash)
                    # Specify the local file path where you want to save the image
                    local_file_path: str = f"{self.museum_name}/images/{image_name}.jpg"

                    # Save the image data to the local file
                    with open(local_file_path, "wb") as image_file:
                        image_file.write(image_data)

                    print(f"Image downloaded successfully and saved as {local_file_path}")
                    return True
                else:
                    print("Image already present")
                    return False
                
            else:
                # Print an error message if the request was not successful
                print("Image cannot be downloaded!")
                print(f"Error: {response.status_code} - {response.text}")
                return False

        except requests.Timeout:
            if n_trial < 5:
                print(f"Trial {n_trial} failed. Sending request again")
                self.download_image(url=url, image_name=image_name, n_trial=n_trial+1)
            else:
                print("Unable to reach link")
                return False
        
    def download_json(self, response_dict: dict, image_name: str) -> None:
        """Download dictionary as a json file with the same name as the corresponding image.

        Args:
            response_dict: Dictionary containing information about the image, to be saved as
                           a json file.
            image_name: Name of the image whose information is contained in response_dict.
        
        """

        if image_name is None or image_name == "":
            return

        if ".jpg" in str(image_name):
            image_name = image_name.rstrip(".jpg")
            
        # replace None values with empty strings in the json
        response_dict = {
            key: "" if value is None else value for key, value in response_dict.items()
            }

        file_path = f"{self.museum_name}/jsons/{image_name}.json"
        with open(file_path, 'w') as json_file:
            json.dump(response_dict, json_file)
        print(f"json downloaded successfully and saved as {file_path}")

    def run_downloading_pipeline(self, n_images_to_download: int = 0) -> None:
        """Main function to run the entire downloading pipeline which saves both the image and
        related json. This function will be museum specific.
        
        Args:
            n_images_to_download: The number of images to download successfully. Defaults
                                  to 0.
        """
        # Check if the needed folders exist in the current directory
        current_directory: str = os.getcwd()
        # hardcoded structure for json and image files path
        # feel free to make this custom
        images_folder: str = os.path.join(current_directory, f'{self.museum_name}/images')
        jsons_folder: str = os.path.join(current_directory, f'{self.museum_name}/jsons')
        
        if not os.path.exists(images_folder):
            # If the "images" folder does not exist, create it
            os.makedirs(images_folder)
            print(f"Created '{self.museum_name}/images' folder in the current directory.")
            
        if not os.path.exists(jsons_folder):
            # If the "jsons" folder does not exist, create it
            os.makedirs(jsons_folder)
            print(f"Created '{self.museum_name}/jsons' folder in the current directory.")
        
        return
