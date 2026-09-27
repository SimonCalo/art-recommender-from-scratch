import os
import pandas as pd
import numpy as np
from helper_functions.src.vector_helpers import create_normalized_vector
user_preferences_database_name = "user_preferences.csv"


class User():
    """A class to handle users and retain their information"""
    
    def __init__(self, user_id: str = None) -> None:
        """method to create a new user instance and initialise (or retrieve)
        their information needed for the project.
        In case a user does not exist in the user_preferences_db, this method
        creates a new row for this user.

        Args:
            user_id (str, optional): The unique id for the user. Defaults to None.
        """
        self.user_id = user_id
        self.user_preferences_database_name = user_preferences_database_name
        # To be replaced with some online table (maybe from supabase)
        self.user_preferences_db: pd.DataFrame = self.load_user_preferences_db()
        self.liked_artworks = []
        self.disliked_artworks = []
        self.recommendations = []
        self.vector = None
        self.user_index = None
        # check if the user already exists in the user preferences table
        if self.user_id in self.user_preferences_db["user_id"].to_list():
            print("entering existing condition")
            self.user_index = self.user_preferences_db.index[
                self.user_preferences_db["user_id"] == self.user_id
            ].tolist()[0]
            # use eval to convert back to lists, which get stored as str in csv files
            self.liked_artworks = eval(
                self.user_preferences_db.at[self.user_index, "liked_artworks"]
                )
            self.disliked_artworks = eval(self.user_preferences_db.at[
                self.user_index, "disliked_artworks"
                ])
            self.vector = eval(self.user_preferences_db.at[self.user_index, "user_vector"])
            self.recommendations = eval(self.user_preferences_db.at[
                self.user_index, "recommendations"
                ])
        # otherwise create a new row in the table for the new user
        else:
            new_row = pd.DataFrame(
                {
                    'user_id': [self.user_id],
                    'liked_artworks': [[]],
                    'disliked_artworks': [[]],
                    'user_vector': [[]],
                    'recommendations': [[]],
                    }
                )

            # Add the new row using concat
            self.user_preferences_db = pd.concat(
                [self.user_preferences_db, new_row], ignore_index=True
                )
            
            # retrieve the index of the newly added row
            self.user_index = self.user_preferences_db.index[
                self.user_preferences_db["user_id"] == self.user_id
            ].tolist()[0]
    
    def update_user_details(self) -> None:
        pass
    
    def delete_user(self) -> None:
        pass
    
    def load_user_preferences_db(self, directory: str = os.getcwd()) -> pd.DataFrame:
        """Function to load the user preferences db.
        If the file is not found in the directory provided, this
        function creates an empty table with the expected schema.
        
        Args:
            directory (str): The directory where this table should be located.
                             Defaults to current working directory: os.getcwd().

        Returns:
            pd.DataFrame: The df corresponding to the user preferences db.
        """
        # get the full path to the file
        user_preferences_database_file: str = os.path.join(
            directory, f'{self.user_preferences_database_name}'
            )
        
        # if the file does not exist, create an empty csv with the correct schema
        if not os.path.exists(user_preferences_database_file):
            df = pd.DataFrame(
                columns=["user_id", "liked_artworks", "disliked_artworks", "user_vector"]
                )
            df.to_csv(user_preferences_database_file, index=False)
        
        return pd.read_csv(user_preferences_database_file)
    
    def add_liked_artworks(self, new_liked_artworks: list) -> None:
        """Add newly liked artworks to the list of artworks liked by
        the user.

        Args:
            new_liked_artworks (list): list of newly liked artworks id.
        """
        self.liked_artworks += new_liked_artworks
        self.user_preferences_db.at[self.user_index, "liked_artworks"] = self.liked_artworks
            
    def add_disliked_artworks(self, new_disliked_artworks: list) -> None:
        """Add newly disliked artworks to the list of artworks disliked by
        the user.

        Args:
            new_disliked_artworks (list): list of newly disliked artworks id.
        """
        self.disliked_artworks += new_disliked_artworks
        self.user_preferences_db.at[self.user_index, "disliked_artworks"] = self.disliked_artworks
    
# TODO: consider including CHROMADBGenerator as a class to import here as well to extract liked and
# disliked vectors simply from the ids
    def create_or_update_user_vector(
        self,
        list_of_new_liked_image_ids: list[str],
        list_of_new_disliked_image_ids: list[str],
        list_of_new_liked_vectors: list[float],
        list_of_new_disliked_vectors: list[float],
    ) -> None:
        """Function to update the vector representation of a user
        (or create it if it has not been created previously).
        The method to create this vector is extremely simple and far from
        optimal. We simply add together all the vectors of the liked artworks
        and subtract the ones of the disliked artworks. The result is then normalised.

        Args:
            list_of_new_liked_image_ids (list[str]): The newly liked image ids.
            list_of_new_disliked_image_ids (list[str]): The newly disliked image ids.
            list_of_new_liked_vectors (list[float]): The vectors of the newly liked images.
            list_of_new_disliked_vectors (list[float]): The vectors of the newly disliked images.
        """
        
        # remove potential duplicates in the lists of new image ids and vectors.
        list_of_new_liked_image_ids = [
            image_id for image_id in list_of_new_liked_image_ids if (
                image_id not in self.liked_artworks
                )
            ]
        list_of_new_liked_vectors = [
            vector for image_id, vector in zip(
                list_of_new_liked_image_ids, list_of_new_liked_vectors
                ) if image_id not in self.liked_artworks
            ]

        list_of_new_disliked_image_ids = [
            image_id for image_id in list_of_new_disliked_image_ids if (
                image_id not in self.disliked_artworks
                )
            ]
        list_of_new_disliked_vectors = [
            vector for image_id, vector in zip(
                list_of_new_disliked_image_ids, list_of_new_disliked_vectors
                ) if image_id not in self.disliked_artworks
            ]
        
        # add the newly liked and disliked images to the ones recorded for the user
        self.add_liked_artworks(new_liked_artworks=list_of_new_liked_image_ids)
        self.add_disliked_artworks(new_disliked_artworks=list_of_new_disliked_image_ids)
        
        # keep the vectors of the liked images and invert the ones of the disliked images
        list_of_new_liked_vectors = [np.array(vector) for vector in list_of_new_liked_vectors]
        list_of_new_disliked_vectors = [
            np.array(vector) * (-1.0) for vector in list_of_new_disliked_vectors
            ]
        # combine the two lists into a final one to create the user vector
        total_list_of_vectors = list_of_new_liked_vectors + list_of_new_disliked_vectors
        if self.vector:
            # A hacky way to take into account previously seen artworks
            # simply add the user vector multiplied by how many artworks had been
            # previously used to create the vector.
            weighing_factor = (
                len(self.liked_artworks) + 
                len(self.disliked_artworks) - 
                len(list_of_new_liked_vectors) - 
                len(list_of_new_disliked_vectors)
                )
            # added for now to be sure it's always a numpy array
            # can be removed once final structure has been determined
            user_vector_array = np.array(self.vector.copy())
            existing_user_vector_scaled = user_vector_array * weighing_factor
            total_list_of_vectors += [existing_user_vector_scaled]
        # convert the resulting numpy array into a list of floats
        self.vector = create_normalized_vector(total_list_of_vectors).tolist()
        self.user_preferences_db.at[self.user_index, "user_vector"] = self.vector
  
    # TODO: replace the directory parameter here and in the load function with a config
    # variable since the directory should be the same in both cases.

    def end_user_session(self, directory: str = os.getcwd()) -> None:
        """Update the user preferences table and save it.

        Args:
            directory (str): The directory where this table should be located.
                             Defaults to current working directory: os.getcwd().
        """

        # get the full path to the file
        user_preferences_database_file: str = os.path.join(
            directory, f'{self.user_preferences_database_name}'
            )
        self.user_preferences_db.to_csv(user_preferences_database_file, index=False)
