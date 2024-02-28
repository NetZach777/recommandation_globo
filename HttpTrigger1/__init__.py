import azure.functions as func
import logging
import json
import os
from azure.storage.blob import BlobServiceClient
import pandas as pd
import io
import pickle
from surprise import SVD


# Configuration de la connexion Azure Blob Storage
connection_string = os.environ["AzureWebJobsStorage"]
container_name = 'model-storage'
model_blob_name = 'best_svd_model.pkl'
df_blob_name = 'df_merged_compressed.pkl'

# Connexion au service Blob
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Fonction pour charger un modèle
def load_model():
    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=model_blob_name)
        model_bytes = blob_client.download_blob().readall()
        loaded_model = pickle.loads(model_bytes)
        return loaded_model
    except Exception as e:
        logging.error(f"Erreur lors du chargement du modèle : {e}")
        return None

# Fonction pour charger un DataFrame
def load_dataframe():
    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=df_blob_name)
        df_bytes = blob_client.download_blob().readall()
        df_merged = pd.read_pickle(io.BytesIO(df_bytes), compression="gzip")
        return df_merged
    except Exception as e:
        logging.error(f"Erreur lors du chargement du DataFrame : {e}")
        return None

# Charger le modèle et le DataFrame au démarrage
loaded_model = load_model()
df_merged = load_dataframe()

# Préparation des données d'interaction (à ajuster en fonction de votre df_merged)
def prepare_interaction_data(df):
    interaction = df[['user_id', 'article_id', 'session_id']].groupby(by=['user_id', 'article_id'], as_index=False).agg('count')
    interaction.rename(columns={'session_id': 'rating'}, inplace=True)
    interaction['rating'] = (interaction['rating'] - interaction['rating'].min()) / (interaction['rating'].max() - interaction['rating'].min())
    return interaction

# Vérifiez si df_merged a été chargé correctement avant de l'utiliser
if df_merged is not None:
    interaction = prepare_interaction_data(df_merged)
    
# Fonction pour obtenir les articles populaires
def get_popular_articles(interaction_df, n=5):
    popular_articles = interaction_df['article_id'].value_counts().head(n).index.tolist()
    return popular_articles

# Fonction de recommandation
def get_recommendations(user_id, model, interaction_df, n=5):
    try:
        if user_id and user_id in interaction_df['user_id'].unique():
            articles = set(interaction_df['article_id'].unique())
            predictions = [model.predict(user_id, article).est for article in articles]
            top_articles = sorted(zip(articles, predictions), key=lambda x: x[1], reverse=True)[:n]
            return [int(article) for article, _ in top_articles]
        else:
            # Retourner les articles populaires si l'user_id est absent ou n'existe pas
            return get_popular_articles(interaction_df, n)
    except Exception as e:
        # Gérer les erreurs spécifiques à la fonction de recommandation
        raise Exception(f"Erreur dans la fonction de recommandation : {str(e)}")

# Fonction principale
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Obtenir le corps de la requête HTTP
        user_id = req.params.get('user_id')
        logging.info('user_id: %s' % user_id)

        # Définir n par défaut
        n = 5
        
        # Si user_id est fourni, le convertir en entier
        if user_id:
            user_id = int(user_id)
            # L'utilisateur existant, renvoie des recommandations
            recommended_articles = get_recommendations(user_id, loaded_model, interaction, n)
            message = "Merci de votre visite ! Voici vos recommandations personnalisees."
        else:
            # Si user_id n'est pas fourni, ne recommande aucun article et affiche un message d'inscription
            user_id = None
            recommended_articles = []
            message = "Bienvenue ! Inscrivez-vous des maintenant et recevez un acces a nos contenus speciaux !"

        # Ajouter ces informations aux journaux
        logging.info(f"Requête reçue. ID utilisateur : {user_id}, n : {n}")

        # Retourner la réponse HTTP
        return func.HttpResponse(
            json.dumps({'user_id': user_id, 'recommendations': recommended_articles, 'message': message}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        # Gérer les erreurs générales
        logging.error(f"Erreur générale : {str(e)}")
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype="application/json"
        )