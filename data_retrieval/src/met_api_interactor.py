from time import sleep
from data_retrieval.src.generic_museum_api_interactor import GenericMuseumApiInteractor


class MetApiInteractor(GenericMuseumApiInteractor):
    """Class to define the configuration and structure for the interactor specific to the
    MET musuem. This class inherits its structure and methods from GenericMuseumApiInteractor.
    """

    def __init__(self) -> None:
        """Instantiate an object of the class using the parent class constructor."""
        super().__init__(museum_name="met")

    def run_downloading_pipeline(self, n_images_to_download: int) -> None:
        """Run the entire pipeline to retrieve and download both images and related jsons
        in a consistent folder structure.

        Args:
            n_images_to_download (int): The number of images to download successfully.
        """
        
        super().run_downloading_pipeline()
        
        # use i to keep track of which records we have already tried to download
        i = 0
        # use images_downloaded to track the number of images successfully downloaded
        images_downloaded = 0
        # the url for the entire image collection available through the met museuem API
        collection_url: str = f"{self.base_url}/objects"
        entire_collection_response: dict = self.get_response_dict(collection_url)
        # limit the number of images to download to the total number of images available
        n_images_to_download = min(
            n_images_to_download, len(entire_collection_response["objectIDs"])
            )
        # only end the process when the desired number of images has been downloaded
        
        while images_downloaded < n_images_to_download:
            artwork_id: str = str(entire_collection_response["objectIDs"][i])
            # extract the specific details about this artwork
            
            artwork_data_url: str = f"{self.base_url}/objects/{artwork_id}"
            artwork_dict: dict = self.get_response_dict(artwork_data_url)

            if self.is_exception(artwork_dict):
                i += 1
                continue

            image_url: str = artwork_dict["primaryImage"]
            image_downloaded = self.download_image(url=image_url, image_name=artwork_id)
            if image_downloaded:
                self.download_json(response_dict=artwork_dict, image_name=artwork_id)
                images_downloaded += 1
            i += 1
            # sleep to avoid triggering robot blocks (error 403)
            sleep(0.5)
