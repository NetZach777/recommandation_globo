import streamlit as st
import requests

def call_azure_function(url, params):
    try:
        response = requests.get(url, params=params)

        # Vérifier la réponse
        response.raise_for_status()

        return response.json()
    except requests.RequestException as e:
        st.error(f"Erreur lors de l'appel à la fonction Azure : {str(e)}")
        return None

# Définition de l'URL de la fonction Azure
azure_function_url = "https://recommandation-svd.azurewebsites.net/api/HttpTrigger1"

# Page d'accueil Streamlit
st.title("Test de la Fonction Azure de recommandation")

# Saisir l'ID utilisateur via l'interface utilisateur
user_id = st.text_input("Entrez l'ID utilisateur")

# Bouton pour déclencher la recommandation
if st.button("Obtenir des recommandations"):
    # Préparer les données de la requête
    params = {'user_id': user_id} if user_id else {}

    # Appeler votre fonction Azure
    result = call_azure_function(azure_function_url, params)

    if result is not None:
        st.success(f"Recommandations pour l'utilisateur {result['user_id']} : {result['recommendations']}")
