from data_retrieval.src.generic_museum_api_interactor import GenericMuseumApiInteractor


class RijksApiInteractor(GenericMuseumApiInteractor):
    """Class to define the configuration and structure for the interactor specific to the
    Rijks museum. This class inherits its structure and methods from
    GenericMuseumApiInteractor.
    """

    def __init__(self) -> None:
        """Instantiate an object of the class using the parent class constructor."""
        super().__init__(museum_name="rijks")

    def run_downloading_pipeline(self, n_images_to_download: int) -> None:
        """Run the entire pipeline to retrieve and download both images and related jsons
        in a consistent folder structure.
        The Rijks museum API requires browsing a specific page and then all the results in that
        page.

        Args:
            n_images_to_download: The number of images to download successfully.
        """
        
        super().run_downloading_pipeline()

        page_url = self.base_url

        # Loop over the pages
        while n_images_to_download > 0:
            # structure the query parameters in the correct format
            # extract the data for all the images on this page
            page_response: dict = self.get_response_dict(url=page_url)
            if page_response == {}:
                continue
            # go through every result in the page
            for item in page_response["orderedItems"]:
                
                artwork_id: str = item["id"].split("/")[-1]
                artwork_dict: dict = self.get_response_dict(url=item["id"])

                if artwork_dict == {}:
                    continue
                image_dict = self.get_response_dict(url=artwork_dict["shows"][0]["id"])
                digitally_shown_id = image_dict["digitally_shown_by"][0]["id"]
                image_dict = self.get_response_dict(url=digitally_shown_id)
                # keep only public domain images
                if (
                     not image_dict["subject_to"][0]["classified_as"][0]["_label"].lower() == "public domain"
                ):
                    continue
                image_url = image_dict["access_point"][0]["id"]
                if image_url is None or image_url.strip() == "":
                    continue
                image_downloaded = self.download_image(url=image_url, image_name=artwork_id)
                if image_downloaded:
                    self.download_json(response_dict=artwork_dict, image_name=artwork_id)
                    n_images_to_download -= 1
                    if n_images_to_download == 0:
                        break
            # go to the next page
            page_url = page_response["next"]["id"]
