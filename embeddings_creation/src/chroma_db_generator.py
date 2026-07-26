"""
This file contains the class ChromaDBGenerator, which allows to create and interact with ChromaDB SQL database.
It is fundamentally a wrapper class to more easily interact with the ChromaDB API, as well as to implement
some additional functionalities.

The class allows to:
- add images and their metadata to the database
- add text data to the database
- retrieve images from the database based on text queries or based on vector similarity
- retrieve diverse sets of images from the database efficiently
"""

# TODO: unify add data to collection methods into one
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions
from chromadb.utils.data_loaders import ImageLoader
import os
import json
from embeddings_creation.config.chroma_db_generator_config import (
    CHROMA_DATA_PATH,
    vector_similarity,
)
import numpy as np
from embeddings_creation.src.data_models import EmbeddingData
from helper_functions.vector_helpers import compute_cosine_similarities


class ChromaDBGenerator:
    """Class to create and interact with ChromaDB SQL database.
    This class allows to store image in vector format and retrieve them using
    text or vector queries.
    """
    
    def __init__(
        self,
        collection_name: str,
        images_path: str,
        jsons_path: str,
        similarity_measure: str = "cosine_similarity",
        include_data_loader: bool = True,
    ) -> None:
        """Instantiate an object of the class.

        Args:
            collection_name (str): Name for the ChromaDB collection of images.
            images_path (str): Path where the images to be stored in the collection are.
            jsons_path (str): Path where the jsons to be stored as metadata in the collection are.
            similarity_measure (str, optional): The method to determine vector similarity.
                                                Defaults to "cosine_similarity".
            include_data_loader (bool, optional): Whether to specify data loader object. Needed
                                                  for images. Defaults to True.
        """
        self.CHROMA_DATA_PATH = CHROMA_DATA_PATH
        self.COLLECTION_NAME = collection_name
        self.images_path = images_path
        self.jsons_path = jsons_path
        self.similarity_measure = similarity_measure
        self.client = chromadb.PersistentClient(path=self.CHROMA_DATA_PATH)
        # currently, this is the only available model for images within ChromaDB
        # alternatively, it's possible to use other methods to generate embeddings and
        # simply store the embeddings in ChromaDB
        self.embedding_func = embedding_functions.OpenCLIPEmbeddingFunction()
        # only include data_loader if specified
        self.image_loader = ImageLoader() if include_data_loader else None
        # create the collection or get it if it already exists
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self.embedding_func,
            data_loader=self.image_loader,
            metadata=vector_similarity[self.similarity_measure],
        )
        self.image_names = []
        self.jsons = []
        
    def retrieve_images_and_jsons(self) -> None:
        """Retrieve all the image names and jsons in the provided paths."""
        # get all files ending with .jpg
        self.image_names = [f for f in os.listdir(self.images_path) if f.endswith(".jpg")]
        
        # for each image, collect the relative metadata
        for image_name in self.image_names:
            json_name = image_name.rstrip(".jpg") + ".json"
            with open(f"{self.jsons_path}/{json_name}", "r") as file:
                json_data = json.load(file)
            
            # remove all items that don't conform to the ChromaDB requirements
            json_data = {
                k: v for k, v in json_data.items() if isinstance(v, (str, int, float, bool))
                }
            self.jsons.append(json_data)
        
    def add_image_data_to_collection(self, add_metadata: bool = False) -> None:
        """Add images data to collection.
        if add_metadata = True, then add the metadata contained in the jsons
        as well. Adding metadata might result in problems due to a non-standardised
        format of the json files.

        Args:
            add_metadata (bool, optional): Whether to add metadata for each image in the collection.
                                           Defaults to False.
        """
        
        self.retrieve_images_and_jsons()
        
        # NOTE: metadata can only be added if the jsons do not contain None values
        metadatas = self.jsons if add_metadata else None
        self.collection.add(
            ids=[image_name.rstrip(".jpg") for image_name in self.image_names],
            uris=[f"{self.images_path}/{image_name}" for image_name in self.image_names],
            metadatas=metadatas,
        )
 
    def add_text_data_to_collection(self, ids: list[str], documents: list[str]) -> None:
        """Add text data to the collection.

        Args:
            ids (list[str]): A list of all the ids for the documents.
            documents (list[str]): The text documents to be added to the collection.
        """
        
        self.collection.add(
            ids=ids,
            documents=documents,
        )
 
    def retrieve_embeddings_of_images(self, images_ids: list[str]) -> list[float]:
        """Retrieve a list of the embeddings of all the chosen images.
        In case an id is incorrect, the method returns no embedding for it, but does
        not throw an exception.
        
        Args:
            images_ids (list[str]): A list of all the image_ids for which we want to retrieve
                                    the vector embeddings.
            
        Returns:
            list[float]: A list of the vector embeddings of the chosen images.
        """
        # In case the list is empty, return an empty list back
        if not images_ids:
            return []
        # Note: if you pass an empty list, this method still returns embeddings
        vector_embeddings = self.collection.get(
            ids=images_ids,
            include=["embeddings"],
            )["embeddings"]
        
        return vector_embeddings
    
    def find_n_most_similar_to_text(
        self,
        query_text: str,
        n: int = 10,
        metadata_filters: dict = None,
        params_to_output: Optional[list[str]] = None,
    ) -> list[EmbeddingData]:
        """Retrieve the n most fitting artworks to a given text query.

        Args:
            query_text (str): The text query.
            n (int, optional): The number of matching results to find. Defaults to 10.
            metadata_filters (dict, optional): A dictionary containing metadata filters.
                                               For more details on how to use this argument, visit:
                                               https://docs.trychroma.com/usage-guide
                                               Defaults to None.
            params_to_output (list[str], optional): A list containing the parameters to output from
                                                    the query. Defaults to
                                                    ["distances", "uris", "embeddings"].

        Returns:
            list[EmbeddingData]: A list of EmbeddingData objects containing the matching results.
        """
        if params_to_output is None:
            params_to_output = ["distances", "uris", "embeddings"]

        if n < 1:
            return []

        # if more output parameters are needed, modify the include argument
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n,
            where=metadata_filters,
            include=params_to_output,
        )
        
        return [
            EmbeddingData(
                id=results["ids"][0][i],
                distance=results["distances"][0][i],
                image_path=results["uris"][0][i],
                embedding=results["embeddings"][0][i]
            )
            for i in range(len(results["ids"][0]))
        ]
        
    def find_n_most_similar_to_image(
        self,
        image_id: str,
        n: int = 10,
        metadata_filters: dict = None,
        params_to_output: Optional[list[str]] = None,
    ) -> list[EmbeddingData]:
        """Retrieve the n most similar artworks to a given artwork.
        
        Args:
            image_id (str): The id of the image to find similar images to.
            n (int, optional): The number of matching results to find. Defaults to 10.
            metadata_filters (dict, optional): A dictionary containing metadata filters.
                                               For more details on how to use this argument, visit:
                                               https://docs.trychroma.com/usage-guide
                                               Defaults to None.
            params_to_output (list[str], optional): A list containing the parameters to output from
                                                    the query. Defaults to
                                                    ["distances", "uris", "embeddings"].
        
        Returns:
            list[EmbeddingData]: A list of EmbeddingData objects containing the matching results.
        """
        if params_to_output is None:
            params_to_output = ["distances", "uris", "embeddings"]

        # retrieve the vector of the chosen image
        vector_embedding = self.retrieve_embeddings_of_images(images_ids=[image_id])[0]
        
        n_most_similar_to_vector = self.find_n_most_similar_to_vector(
            vector=vector_embedding,
            n=n,
            metadata_filters=metadata_filters,
            params_to_output=params_to_output,
            )
        
        return n_most_similar_to_vector
    
    def find_n_most_similar_to_vector(
        self,
        vector: list[float],
        n: int = 10,
        params_to_output: Optional[list[str]] = None,
        metadata_filters: Optional[dict] = None,
        image_ids_to_be_distant_from: Optional[list[str]] = None,
        similarity_threshold: float = 0.9,
        factor_for_extra_retrieval: int = 5,
        similarity_threshold_step: float = 0.05,
        factor_increase_step: int = 1,
    ) -> list[EmbeddingData]:
        """Retrieve the n most similar artworks to a given embedding vector.

        Args:
            vector (list[float]): The embedding vector to find similar artworks to.
            n (int, optional): The number of matching results to find. Defaults to 10.
            metadata_filters (dict, optional): A dictionary containing metadata filters.
                                               For more details on how to use this argument, visit:
                                               https://docs.trychroma.com/usage-guide
                                               Defaults to None.
            params_to_output (list[str], optional): A list containing the parameters to output from
                                                    the query. Defaults to
                                                    ["distances", "uris", "embeddings"].
            image_ids_to_be_distant_from (list[str], optional): Image IDs that we want the output
                                                                images to be different from.
            similarity_threshold (float, optional): A threshold for excluding results considered too
                                                    similar to the provided image IDs to be distant
                                                    from. Defaults to 0.9.
            factor_for_extra_retrieval (int, optional): Factor to increase query size to compensate
                                                        for potential filtering. Defaults to 5.
            similarity_threshold_step (float, optional): How much to decrease the similarity threshold
                                                         in each consecutive recursive call. Defaults to 
                                                         0.05.
            factor_increase_step (int, optional): How much to increase the retrieval factor
                                                in each recursive call. Defaults to 1.

        Returns:
            list[EmbeddingData]: A list of EmbeddingData objects containing the matching results.
        """
        if params_to_output is None:
            params_to_output = ["distances", "uris", "embeddings"]

        if n < 1:
            return []

        query_size = (n * factor_for_extra_retrieval) if image_ids_to_be_distant_from else n

        # if more output parameters are needed, modify the include argument
        results = self.collection.query(
            query_embeddings=[vector],
            n_results=query_size,
            where=metadata_filters,
            include=params_to_output,
        )

        if image_ids_to_be_distant_from is None:
            return [
                EmbeddingData(
                    id=results["ids"][0][i],
                    distance=results["distances"][0][i],
                    image_path=results["uris"][0][i],
                    embedding=results["embeddings"][0][i]
                )
                for i in range(len(results["ids"][0]))
            ]

        embeddings_to_be_distant_from = self.collection.get(
            ids=image_ids_to_be_distant_from,
            include=["embeddings"]
        )["embeddings"]

        images_similarities = compute_cosine_similarities(
            vectors1=np.array(results["embeddings"][0]),
            vectors2=np.array(embeddings_to_be_distant_from)
        )

        # mark all the images to be removed
        remove_mask = np.any(images_similarities > similarity_threshold, axis=1)

        result_to_output = [
            EmbeddingData(
                id=results["ids"][0][i],
                distance=results["distances"][0][i],
                image_path=results["uris"][0][i],
                embedding=results["embeddings"][0][i]
            )
            for i in range(len(results["ids"][0])) if not remove_mask[i]
        ]

        if len(result_to_output) >= n:
            return result_to_output[:n]

        # if we were not able to retrieve enough images
        # call the function recursively with a lower similarity threshold
        # and a higher factor to extract more images
        return self.find_n_most_similar_to_vector(
            vector=vector,
            n=n,
            metadata_filters=metadata_filters,
            params_to_output=params_to_output,
            image_ids_to_be_distant_from=image_ids_to_be_distant_from,
            similarity_threshold=similarity_threshold-similarity_threshold_step,
            factor_for_extra_retrieval=factor_for_extra_retrieval+factor_increase_step,
            similarity_threshold_step=similarity_threshold_step,
            factor_increase_step=factor_increase_step,
        )

    def efficient_diverse_vectors_retrieval(
            self, n: int = 40, image_paths_to_avoid: Optional[list[str]] = None
            ) -> list[str]:
        """Efficiently retrieve a set of diverse vectors from the collection.
        Diversity is defined as low absolute overlap of a vector with the selected ones.
        This method works by selecting a random set of basis directions and retrieving every time
        the closest vector in the collection to this random direction.

        Args:
            n (int, optional): The number of ids to retrieve. Defaults to 40.
            image_paths_to_avoid (Optional[list[str]]): List of images not to be included in the
                                                        output. Defaults to None.

        Returns:
            list[str]: A set of diverse images.
        """
        if image_paths_to_avoid is None:
            image_paths_to_avoid = []
        selected_ids = []
        # extract sample embedding for dimensionality
        # FIXME: this retrieves all embeddings in the collection. Can we optimise this?
        result = self.collection.get(include=['embeddings'])
        # Determine the dimensionality of your embeddings space
        dimensionality = len(result['embeddings'][0])
        
        basis_vector = np.zeros(dimensionality).tolist()
        
        random_basis_dimensions = np.random.choice(a=dimensionality, size=n, replace=False)
        
        for basis_dimension in random_basis_dimensions:
            basis_vector[basis_dimension] = 1.0
            new_id_not_found = True
            i = 1
            while new_id_not_found:
                candidate = self.find_n_most_similar_to_vector(vector=basis_vector, n=i)[i - 1]
                i += 1
                candidate_image_path = candidate.image_path
                if (
                    candidate_image_path not in selected_ids
                    ) and (
                        candidate_image_path not in image_paths_to_avoid
                        ):
                    selected_ids.append(candidate_image_path)
                    new_id_not_found = False
                    basis_vector[basis_dimension] = 0.0

        return selected_ids

    def mmr_vector_search(self, n: int = 10, lambda_param: float = 0.5) -> list[str]:
        """Perform a diverse vector search using MMR (Maximal Marginal Relevance).

        This function retrieves a set of n diverse vector IDs from the given ChromaDB
        collection using the MMR algorithm. It balances between relevance and diversity of the
        selected vectors.

        Args:
            n: Number of diverse vectors to return. Defaults to 10.
            lambda_param: Lambda parameter for MMR. Controls the trade-off between
                diversity (higher values) and similarity (lower values).
                Must be between 0 and 1. Defaults to 0.5.

        Returns:
            A list of n diverse vector IDs from the collection.

        Raises:
            ValueError: If lambda_param is not between 0 and 1.
        """
        if not 0 <= lambda_param <= 1:
            raise ValueError("lambda_param must be between 0 and 1")

        # Get all embeddings and IDs from the collection
        result = self.collection.get(include=['embeddings'])
        all_embeddings = np.array(result['embeddings'])
        all_ids = result['ids']

        # Initialize
        selected_ids = []
        selected_embeddings = []
        remaining_indices = list(range(len(all_ids)))

        # Select the first vector randomly
        first_index = np.random.choice(remaining_indices)
        selected_ids.append(all_ids[first_index])
        selected_embeddings.append(all_embeddings[first_index])
        remaining_indices.remove(first_index)

        # Select the rest using MMR
        for _ in range(1, n):
            if not remaining_indices:
                break

            best_score = float('-inf')
            best_index = -1

            for idx in remaining_indices:
                candidate_embedding = all_embeddings[idx]

                # Compute similarity to selected embeddings
                # abs applied on a multidimensional object just takes the abs of each element
                sim_selected = np.abs(np.dot(candidate_embedding, np.array(selected_embeddings).T))
                max_sim_selected = np.max(sim_selected) if len(sim_selected) > 0 else 0

                # Compute diversity score
                # diversity_score = np.min(1 - sim_selected) if len(sim_selected) > 0 else 1
                diversity_score = -1*max_sim_selected

                # Compute MMR score
                mmr_score = lambda_param * diversity_score - (1 - lambda_param) * max_sim_selected

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_index = idx

            selected_ids.append(all_ids[best_index])
            selected_embeddings.append(all_embeddings[best_index])
            remaining_indices.remove(best_index)

        return selected_ids
