import streamlit as st
# Configuration de la page
st.set_page_config(
    page_title="Rapport",
    layout="wide",
    initial_sidebar_state="expanded"
)
import pandas as pd
from PIL import Image
import json
import os
from pathlib import Path
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas


# Initialiser la session_state si ce n'est pas déjà fait
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}

# Charger les données existantes - MODIFIÉ pour ne pas charger automatiquement les fichiers sauvegardés
def load_data():
    """
    Charge uniquement les données de la session, pas des fichiers sauvegardés
    """
    # Vérifier si nous avons déjà des données dans la session
    if 'user_data' in st.session_state and st.session_state.user_data:
        return st.session_state.user_data
    
    # Ne plus charger automatiquement les fichiers
    return {}

# Sauvegarder les données
def save_data(data):
    """
    Sauvegarde les données dans un fichier JSON avec un nom de fichier unique basé sur le nom de l'entreprise et un horodatage
    """
    # Sauvegarder dans la session state (persistante pendant la session utilisateur)
    st.session_state.user_data = data
    
    # Créer le dossier de sauvegarde s'il n'existe pas
    save_dir = "saved_data"
    os.makedirs(save_dir, exist_ok=True)
    
    # Générer un nom de fichier unique
    company_name = data.get('ident_rs', 'entreprise').replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{save_dir}/{company_name}_{timestamp}.json"
    
    # Sauvegarder dans un fichier local
    try:
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return filename
    except Exception as e:
        st.warning(f"Erreur lors de la sauvegarde: {str(e)}")
        return None

# Charger les anciennes entrées
saved_data = load_data()

# Fonction pour créer des inputs avec persistance - MODIFIÉ pour supprimer la sauvegarde automatique
def create_input(label, default_value="", key=None, text_area=False, height=None):
    # Récupérer la valeur sauvegardée si elle existe
    saved_value = saved_data.get(key, default_value)
    
    if text_area:
        if height:
            user_input = st.text_area(label, value=saved_value, key=key, height=height)
        else:
            user_input = st.text_area(label, value=saved_value, key=key)
    else:
        user_input = st.text_input(label, value=saved_value, key=key)
    
    # Stocker la valeur dans saved_data sans sauvegarder automatiquement
    if user_input != saved_data.get(key):
        saved_data[key] = user_input
    
    return user_input

# Fonction pour les tables éditables avec persistance - MODIFIÉ pour supprimer la sauvegarde automatique
def create_editable_table(data, key):
    # Récupérer les données sauvegardées
    saved_table = saved_data.get(key, data)
    df = pd.DataFrame(saved_table)
    
    # Créer l'éditeur de données
    edited_df = st.data_editor(df, key=key, num_rows="dynamic")
    
    # Mettre à jour saved_data sans sauvegarder automatiquement
    if not edited_df.equals(df):
        saved_data[key] = edited_df.to_dict('records')
    
    return edited_df

def create_expandable_table(title, data, key):
    with st.expander(title):
        return create_editable_table(data, key)

# Fonction pour créer le tableau de comparaison des concurrents avec inputs
def create_competitor_comparison_table(key):
    # Définir les critères et concurrents par défaut - tous vides
    default_criteres = ["", "", "", "", "", "", "", ""]
    default_concurrents = ["", "", "", "", "", "", ""]
    
    # Récupérer les concurrents sauvegardés ou utiliser les valeurs par défaut
    concurrents = []
    for i in range(1, len(default_concurrents)+1):
        comp_name = create_input(f"Nom du concurrent {i}", "", f"competitor_name_{i}")
        concurrents.append(comp_name)
    
    # Valeurs par défaut du tableau
    default_values = {
        "Critères/Concurrents": default_criteres
    }
    
    # Ajouter les valeurs par défaut pour chaque concurrent
    for i, comp in enumerate(concurrents):
        default_values[comp if comp else f"Concurrent {i+1}"] = ["", "", "", "", "", "", "", ""]
    
    # Récupérer les données sauvegardées ou utiliser les valeurs par défaut
    saved_table = saved_data.get(key, default_values)
    
    # Permettre la modification du titre de la colonne "Critères/Concurrents"
    criteres_column_name = create_input("Titre de la colonne des critères", "Critères/Concurrents", "criteres_column_name")
    
    # Mettre à jour le nom de la colonne dans les données sauvegardées
    if "Critères/Concurrents" in saved_table and criteres_column_name != "Critères/Concurrents":
        saved_table[criteres_column_name] = saved_table.pop("Critères/Concurrents")
    
    # Créer le dataframe
    df = pd.DataFrame(saved_table)
    
    # Utiliser le nouveau nom de colonne pour l'index
    if criteres_column_name in df.columns:
        df = df.set_index(criteres_column_name)
    else:
        # Si le nom personnalisé n'est pas trouvé, utiliser la première colonne comme index
        df = df.set_index(df.columns[0])
    
    # Permettre l'édition des valeurs du tableau
    st.write("### Tableau Comparatif Détaillé des Concurrents")
    st.write("Modifiez les valeurs en cliquant dessus (+ : présent, - : absent, T : partiellement présent)")
    
    edited_df = st.data_editor(
        df, 
        key=key,
        height=400,
        use_container_width=True
    )
    
    # Mettre à jour saved_data sans sauvegarder automatiquement
    if not edited_df.equals(df):
        # Ajouter la colonne d'index comme une colonne normale pour la sauvegarde
        edited_df_save = edited_df.reset_index()
        
        # Renommer la colonne d'index si nécessaire
        if edited_df_save.columns[0] != criteres_column_name:
            edited_df_save = edited_df_save.rename(columns={edited_df_save.columns[0]: criteres_column_name})
        
        saved_data[key] = edited_df_save.to_dict('list')
    
    # Mettre à jour le nom de la colonne des critères sans sauvegarde automatique
    saved_data["criteres_column_name"] = criteres_column_name
    
    # Afficher la légende
    st.write("**Légende :**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("• + : Service présent")
    with col2:
        st.write("• - : Service absent")
    with col3:
        st.write("• T : Service partiellement présent")
    
    return edited_df, criteres_column_name, concurrents

# Fonction pour créer le Business Model Canvas avec inputs
def create_business_model_canvas(key_prefix):
    st.write("## Business Model Canvas")
    
    # Définir les couleurs pour chaque section du BMC
    bmc_colors = {
        "partenaires": "#ffadb9",    # Rose
        "activites": "#b388ff",      # Violet
        "proposition": "#81c784",     # Vert
        "relations": "#ffb74d",      # Orange
        "segments": "#4fc3f7",       # Bleu
        "ressources": "#b388ff",     # Violet
        "canaux": "#ffb74d",         # Orange
        "couts": "#ffd54f",          # Jaune
        "revenus": "#b388ff"         # Violet
    }
    
    # Créer le canvas avec 3 rangées
    st.write("#### Cliquez dans chaque case pour modifier le contenu")
    
    # Première rangée: Partenaires Clés, Activités Clés, etc.
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"<div style='background-color:{bmc_colors['partenaires']};padding:10px;border-radius:5px;height:250px;'>", unsafe_allow_html=True)
        st.write("**Partenaires Clés**")
        partenaires = create_input("", 
                                "", 
                                f"{key_prefix}_partenaires",
                                text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"<div style='background-color:{bmc_colors['activites']};padding:10px;border-radius:5px;height:250px;'>", unsafe_allow_html=True)
        st.write("**Activités Clés**")
        activites = create_input("", 
                               "", 
                               f"{key_prefix}_activites",
                               text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"<div style='background-color:{bmc_colors['proposition']};padding:10px;border-radius:5px;height:250px;'>", unsafe_allow_html=True)
        st.write("**Proposition de Valeur**")
        proposition = create_input("", 
                                 "", 
                                 f"{key_prefix}_proposition",
                                 text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"<div style='background-color:{bmc_colors['relations']};padding:10px;border-radius:5px;height:250px;'>", unsafe_allow_html=True)
        st.write("**Relations avec les Clients**")
        relations = create_input("", 
                              "", 
                              f"{key_prefix}_relations",
                              text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"<div style='background-color:{bmc_colors['segments']};padding:10px;border-radius:5px;height:250px;'>", unsafe_allow_html=True)
        st.write("**Segments de Clientèle**")
        segments = create_input("", 
                             "", 
                             f"{key_prefix}_segments",
                             text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Deuxième rangée
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.write("")
    
    with col2:
        st.markdown(f"<div style='background-color:{bmc_colors['ressources']};padding:10px;border-radius:5px;height:230px;'>", unsafe_allow_html=True)
        st.write("**Ressources Clés**")
        ressources = create_input("", 
                               "", 
                               f"{key_prefix}_ressources",
                               text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.write("")
    
    with col4:
        st.markdown(f"<div style='background-color:{bmc_colors['canaux']};padding:10px;border-radius:5px;height:230px;'>", unsafe_allow_html=True)
        st.write("**Canaux**")
        canaux = create_input("", 
                           "", 
                           f"{key_prefix}_canaux",
                           text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col5:
        st.write("")
    
    # Troisième rangée
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        st.markdown(f"<div style='background-color:{bmc_colors['couts']};padding:10px;border-radius:5px;height:150px;'>", unsafe_allow_html=True)
        st.write("**Structure de Coûts**")
        couts = create_input("", 
                          "", 
                          f"{key_prefix}_couts",
                          text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.write("")
    
    with col3:
        st.markdown(f"<div style='background-color:{bmc_colors['revenus']};padding:10px;border-radius:5px;height:150px;'>", unsafe_allow_html=True)
        st.write("**Sources de Revenus**")
        revenus = create_input("", 
                            "", 
                            f"{key_prefix}_revenus",
                            text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)

def generate_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=52, leftMargin=52, topMargin=52, bottomMargin=18)
    story = []
    
    # Convertir les données de tableau de format "records" au format "colonnes" attendu
    def convert_table_format(table_key):
        if table_key in saved_data and isinstance(saved_data[table_key], list):
            # Si les données sont au format liste de dictionnaires (format 'records')
            records = saved_data[table_key]
            
            # Convertir en dictionnaire de listes (format 'columns')
            columns_dict = {}
            if records:
                # Initialiser toutes les colonnes possibles
                for record in records:
                    for key in record.keys():
                        if key not in columns_dict:
                            columns_dict[key] = []
                
                # Remplir avec les valeurs
                for column in columns_dict.keys():
                    for record in records:
                        if column in record:
                            columns_dict[column].append(record[column])
                        else:
                            columns_dict[column].append("")  # Valeur par défaut si manquante
                
                # Remplacer par le nouveau format
                saved_data[table_key] = columns_dict
    
    # Convertir toutes les tables nécessaires
    tables_to_convert = [
        'marche_cibles_table', 
        'marche_swot_table', 
        'marche_marketing_table',
        'marche_concurrents_table',
        'marche_comparison_table',
        'marche_matrice_table',
        'competitors_comparison_table',
        'modele_partenaires',
        'modele_activites',
        'modele_proposition',
        'modele_relations',
        'modele_segments',
        'modele_ressources',
        'modele_couts',
        'modele_canaux',
        'modele_revenus',
        'projections_table'
    ]
    
    for table_key in tables_to_convert:
        convert_table_format(table_key)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'title',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    heading1_style = ParagraphStyle(
        'Heading1',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=10
    )
    heading2_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=8
    )
    normal_style = styles['Normal']
    
    # Crée un style pour les en-têtes verticaux des colonnes
    header_style = ParagraphStyle(
        'Header',
        parent=normal_style,
        fontSize=8,
        alignment=TA_CENTER,
    )
    
    # Fonction pour créer un tableau avec des paragraphes pour le contenu cellulaire
    def create_styled_table(data, colWidths, style_commands=None):
        # Convertir le contenu des cellules en paragraphes pour un meilleur rendu
        processed_data = []
        for row in data:
            processed_row = []
            for cell in row:
                if isinstance(cell, str):
                    processed_row.append(Paragraph(cell, normal_style))
                else:
                    processed_row.append(cell)
            processed_data.append(processed_row)
        
        # Créer le tableau avec les données formatées
        table = Table(processed_data, colWidths=colWidths)
        
        # Appliquer le style par défaut
        default_style = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centre tout le contenu par défaut
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ]
        
        # Ajouter les commandes de style personnalisées
        if style_commands:
            default_style.extend(style_commands)
        
        table.setStyle(TableStyle(default_style))
        return table
    
    # Titre principal
    story.append(Paragraph(saved_data.get('projet_titre', "Rapport"), title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Présentation du projet
    story.append(Paragraph("PRÉSENTATION DU PROJET", heading1_style))
    
    # Description du projet
    story.append(Paragraph("1. Description du Projet", heading2_style))
    story.append(Paragraph(f"<b>Problématique :</b> {saved_data.get('pres_prob', '')}", normal_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Processez les retours à la ligne pour les champs texte
    solution_lines = saved_data.get('pres_solution', '').split('\n')
    story.append(Paragraph("<b>Solution proposée :</b>", normal_style))
    for line in solution_lines:
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Fiche d'identité
    story.append(Paragraph("2. Fiche d'Identité", heading2_style))
    identity_data = [
        ["Information", "Détail"],
        ["Raison sociale", saved_data.get('ident_rs', '')],
        ["Slogan", saved_data.get('ident_slogan', '')],
        ["Objet social", saved_data.get('ident_objet_social', '')],
        ["Domaines d'activité", saved_data.get('ident_domaines', '')],
        ["Siège social", saved_data.get('ident_siege', '')],
        ["Forme juridique", saved_data.get('ident_forme', '')],
        ["Nombre d'associés", saved_data.get('ident_associes', '')],
        ["Valeurs", saved_data.get('ident_valeurs', '')]
    ]
    
    identity_table = create_styled_table(
        identity_data, 
        colWidths=[doc.width/3.0, doc.width*2/3.0],
        style_commands=[('ALIGN', (0, 0), (0, -1), 'LEFT')]  # Aligner la première colonne à gauche
    )
    story.append(identity_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Objectifs et Vision
    story.append(Paragraph("3. Objectifs et Vision", heading2_style))
    story.append(Paragraph("<b>Objectifs Principaux :</b>", normal_style))
    for line in saved_data.get('pres_objectifs', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("<b>Objectifs de Développement Durable :</b>", normal_style))
    for line in saved_data.get('pres_odd', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(f"<b>Mission :</b> {saved_data.get('pres_mission', '')}", normal_style))
    story.append(Paragraph(f"<b>Vision :</b> {saved_data.get('pres_vision', '')}", normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Réalisations
    story.append(Paragraph("4. Réalisations Accomplies", heading2_style))
    for line in saved_data.get('pres_realisations', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Analyse de Marché
    story.append(Paragraph("ANALYSE DE MARCHÉ", heading1_style))
    
    # Tendances
    story.append(Paragraph("1. Tendances du Marché", heading2_style))
    for line in saved_data.get('marche_tendances', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Cibles Principales
    story.append(Paragraph("2. Cibles Principales", heading2_style))
    if 'marche_cibles_table' in saved_data and isinstance(saved_data['marche_cibles_table'], dict):
        segments = saved_data['marche_cibles_table'].get('Segment', [])
        benefices = saved_data['marche_cibles_table'].get('Bénéfices', [])
        
        if segments and benefices:
            cibles_data = [["Segment", "Bénéfices"]]
            for i in range(min(len(segments), len(benefices))):
                cibles_data.append([segments[i], benefices[i]])
            
            cibles_table = create_styled_table(
                cibles_data, 
                colWidths=[doc.width/2.0, doc.width/2.0],
                style_commands=[('ALIGN', (0, 1), (0, -1), 'LEFT'), ('ALIGN', (1, 1), (1, -1), 'LEFT')]
            )
            story.append(cibles_table)
        else:
            # Table vide en cas de données manquantes
            default_cibles_data = [
                ["Segment", "Bénéfices"],
                ["", ""],
                ["", ""]
            ]
            cibles_table = create_styled_table(
                default_cibles_data,
                colWidths=[doc.width/2.0, doc.width/2.0],
                style_commands=[('ALIGN', (0, 1), (0, -1), 'LEFT'), ('ALIGN', (1, 1), (1, -1), 'LEFT')]
            )
            story.append(cibles_table)
    else:
        # Table vide en cas de données manquantes
        default_cibles_data = [
            ["Segment", "Bénéfices"],
            ["", ""],
            ["", ""]
        ]
        cibles_table = create_styled_table(
            default_cibles_data,
            colWidths=[doc.width/2.0, doc.width/2.0],
            style_commands=[('ALIGN', (0, 1), (0, -1), 'LEFT'), ('ALIGN', (1, 1), (1, -1), 'LEFT')]
        )
        story.append(cibles_table)
    
    story.append(Spacer(1, 0.2*inch))
    
    # SWOT - Utiliser les données remplies par l'utilisateur dans Streamlit
    story.append(Paragraph("3. Analyse SWOT", heading2_style))
    
    # Vérifier si les données SWOT existent et sont utilisables
    if 'marche_swot_table' in saved_data:
        swot_data = None
        
        # Cas 1: Format dictionnaire
        if isinstance(saved_data['marche_swot_table'], dict):
            categories = saved_data['marche_swot_table'].get('Catégorie', [])
            points = saved_data['marche_swot_table'].get('Points', [])
            
            if categories and points and len(categories) > 0 and len(points) > 0:
                swot_data = [["Catégorie", "Points"]]
                for i in range(min(len(categories), len(points))):
                    swot_data.append([categories[i], points[i]])
        
        # Si on a réussi à récupérer des données, créer le tableau
        if swot_data and len(swot_data) > 1:
            swot_table = create_styled_table(
                swot_data,
                colWidths=[doc.width/3.0, doc.width*2/3.0],
                style_commands=[('ALIGN', (0, 1), (0, -1), 'LEFT'), ('ALIGN', (1, 1), (1, -1), 'LEFT')]
            )
            story.append(swot_table)
        else:
            # Table vide en cas de données manquantes
            default_swot_data = [
                ["Catégorie", "Points"],
                ["Forces", ""],
                ["Faiblesses", ""],
                ["Opportunités", ""],
                ["Menaces", ""]
            ]
            swot_table = create_styled_table(
                default_swot_data,
                colWidths=[doc.width/3.0, doc.width*2/3.0],
                style_commands=[('ALIGN', (0, 1), (0, -1), 'LEFT'), ('ALIGN', (1, 1), (1, -1), 'LEFT')]
            )
            story.append(swot_table)
    else:
        # Table vide en cas de données manquantes
        default_swot_data = [
            ["Catégorie", "Points"],
            ["Forces", ""],
            ["Faiblesses", ""],
            ["Opportunités", ""],
            ["Menaces", ""]
        ]
        swot_table = create_styled_table(
            default_swot_data,
            colWidths=[doc.width/3.0, doc.width*2/3.0],
            style_commands=[('ALIGN', (0, 1), (0, -1), 'LEFT'), ('ALIGN', (1, 1), (1, -1), 'LEFT')]
        )
        story.append(swot_table)
    
    story.append(Spacer(1, 0.2*inch))
    
    # Marketing Mix
    story.append(Paragraph("4. Marketing Mix (4P)", heading2_style))
    if 'marche_marketing_table' in saved_data and isinstance(saved_data['marche_marketing_table'], dict):
        elements = saved_data['marche_marketing_table'].get('Élément', [])
        strategies = saved_data['marche_marketing_table'].get('Stratégie', [])
        
        if elements and strategies:
            marketing_data = [["Élément", "Stratégie"]]
            for i in range(min(len(elements), len(strategies))):
                marketing_data.append([elements[i], strategies[i]])
            
            marketing_table = create_styled_table(
                marketing_data, 
                colWidths=[doc.width/3.0, doc.width*2/3.0],
                style_commands=[('ALIGN', (0, 1), (0, -1), 'LEFT'), ('ALIGN', (1, 1), (1, -1), 'LEFT')]
            )
            story.append(marketing_table)
        else:
            # Table vide en cas de données manquantes
            default_marketing_data = [
                ["Élément", "Stratégie"],
                ["Produit", ""],
                ["Prix", ""],
                ["Place", ""],
                ["Promotion", ""]
            ]
            marketing_table = create_styled_table(
                default_marketing_data,
                colWidths=[doc.width/3.0, doc.width*2/3.0],
                style_commands=[('ALIGN', (0, 1), (0, -1), 'LEFT'), ('ALIGN', (1, 1), (1, -1), 'LEFT')]
            )
            story.append(marketing_table)
    else:
        # Table vide en cas de données manquantes
        default_marketing_data = [
            ["Élément", "Stratégie"],
            ["Produit", ""],
            ["Prix", ""],
            ["Place", ""],
            ["Promotion", ""]
        ]
        marketing_table = create_styled_table(
            default_marketing_data,
            colWidths=[doc.width/3.0, doc.width*2/3.0],
            style_commands=[('ALIGN', (0, 1), (0, -1), 'LEFT'), ('ALIGN', (1, 1), (1, -1), 'LEFT')]
        )
        story.append(marketing_table)
    
    story.append(Spacer(1, 0.2*inch))
    
    # Analyse Concurrentielle
    story.append(Paragraph("5. Analyse Concurrentielle", heading2_style))
    story.append(Paragraph("Tableau Comparatif des Concurrents", styles['Heading3']))
    if 'marche_concurrents_table' in saved_data and isinstance(saved_data['marche_concurrents_table'], dict):
        types = saved_data['marche_concurrents_table'].get('Type', [])
        noms = saved_data['marche_concurrents_table'].get('Nom', [])
        locs = saved_data['marche_concurrents_table'].get('Localisation', [])
        descs = saved_data['marche_concurrents_table'].get('Description', [])
        
        if types and noms and locs and descs:
            concurrents_data = [["Type", "Nom", "Localisation", "Description"]]
            for i in range(min(len(types), len(noms), len(locs), len(descs))):
                concurrents_data.append([types[i], noms[i], locs[i], descs[i]])
            
            # Une table plus compacte pour les concurrents
            concurrents_table = create_styled_table(
                concurrents_data, 
                colWidths=[doc.width/6.0, doc.width/6.0, doc.width/6.0, doc.width/2.0],
                style_commands=[
                    ('ALIGN', (0, 1), (-1, -1), 'LEFT'),  # Aligner tout le contenu à gauche
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                ]
            )
            story.append(concurrents_table)
        else:
            # Table vide en cas de données manquantes
            default_concurrents_data = [
                ["Type", "Nom", "Localisation", "Description"],
                ["", "", "", ""],
                ["", "", "", ""],
                ["", "", "", ""]
            ]
            concurrents_table = create_styled_table(
                default_concurrents_data, 
                colWidths=[doc.width/6.0, doc.width/6.0, doc.width/6.0, doc.width/2.0],
                style_commands=[
                    ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                ]
            )
            story.append(concurrents_table)
    else:
        # Table vide en cas de données manquantes
        default_concurrents_data = [
            ["Type", "Nom", "Localisation", "Description"],
            ["", "", "", ""],
            ["", "", "", ""],
            ["", "", "", ""]
        ]
        concurrents_table = create_styled_table(
            default_concurrents_data, 
            colWidths=[doc.width/6.0, doc.width/6.0, doc.width/6.0, doc.width/2.0],
            style_commands=[
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
            ]
        )
        story.append(concurrents_table)
    
    # Tableau Comparatif Détaillé des Concurrents
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Tableau Comparatif Détaillé des Concurrents", styles['Heading3']))
    
    if 'competitors_comparison_table' in saved_data:
        # Récupérer le nom personnalisé de la colonne des critères
        criteres_column_name = saved_data.get("criteres_column_name", "Critères/Concurrents")
        
        # Récupérer les critères
        if isinstance(saved_data['competitors_comparison_table'], dict):
            criteres = saved_data['competitors_comparison_table'].get(criteres_column_name, [])
            if not criteres:
                criteres = saved_data['competitors_comparison_table'].get('Critères/Concurrents', [])
                
            # Récupérer les noms des concurrents
            competitor_names = []
            for i in range(1, 8):  # Max 7 concurrents
                comp_name = saved_data.get(f"competitor_name_{i}", "")
                if comp_name:
                    competitor_names.append(comp_name)
            
            # Préparer les données du tableau
            if criteres:
                # Créer des en-têtes horizontaux au lieu de verticaux
                competitors_data = [[criteres_column_name] + competitor_names]
                
                for i, critere in enumerate(criteres):
                    row = [critere]
                    for comp in competitor_names:
                        values = saved_data['competitors_comparison_table'].get(comp, [])
                        if i < len(values):
                            row.append(values[i])
                        else:
                            row.append("")
                    competitors_data.append(row)
                
                # Créer un tableau adapté avec des colonnes adaptées
                col_widths = [doc.width/3.0]  # Première colonne plus large
                col_widths.extend([doc.width/(3.0*len(competitor_names))]*len(competitor_names))  # Colonnes des concurrents 
                
                # Créer le tableau
                comp_table = create_styled_table(
                    competitors_data,
                    colWidths=col_widths,
                    style_commands=[
                        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Aligner première colonne à gauche
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),  
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4), 
                        ('TOPPADDING', (0, 0), (-1, -1), 4),   
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4) 
                    ]
                )
                story.append(comp_table)
                
                # Ajouter la légende
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph("<b>Légende :</b>", normal_style))
                story.append(Paragraph("• + : Service présent", normal_style))
                story.append(Paragraph("• - : Service absent", normal_style))
                story.append(Paragraph("• T : Service partiellement présent", normal_style))
            else:
                # Table vide en cas de données manquantes
                default_comp_data = [
                    ["Critère", "", "", ""],
                    ["", "", "", ""],
                    ["", "", "", ""],
                    ["", "", "", ""],
                    ["", "", "", ""]
                ]
                comp_table = create_styled_table(
                    default_comp_data,
                    colWidths=[doc.width/2.0, doc.width/6.0, doc.width/6.0, doc.width/6.0],
                    style_commands=[
                        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                    ]
                )
                story.append(comp_table)
                
                # Ajouter la légende
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph("<b>Légende :</b>", normal_style))
                story.append(Paragraph("• + : Service présent", normal_style))
                story.append(Paragraph("• - : Service absent", normal_style))
                story.append(Paragraph("• T : Service partiellement présent", normal_style))
        else:
            # Table vide en cas de données manquantes
            default_comp_data = [
                ["Critère", "", "", ""],
                ["", "", "", ""],
                ["", "", "", ""],
                ["", "", "", ""],
                ["", "", "", ""]
            ]
            comp_table = create_styled_table(
                default_comp_data,
                colWidths=[doc.width/2.0, doc.width/6.0, doc.width/6.0, doc.width/6.0],
                style_commands=[
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                ]
            )
            story.append(comp_table)
            
            # Ajouter la légende
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph("<b>Légende :</b>", normal_style))
            story.append(Paragraph("• + : Service présent", normal_style))
            story.append(Paragraph("• - : Service absent", normal_style))
            story.append(Paragraph("• T : Service partiellement présent", normal_style))
    else:
        # Table vide en cas de données manquantes
        default_comp_data = [
            ["Critère", "", "", ""],
            ["", "", "", ""],
            ["", "", "", ""],
            ["", "", "", ""],
            ["", "", "", ""]
        ]
        comp_table = create_styled_table(
            default_comp_data,
            colWidths=[doc.width/2.0, doc.width/6.0, doc.width/6.0, doc.width/6.0],
            style_commands=[
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
            ]
        )
        story.append(comp_table)
        
        # Ajouter la légende
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("<b>Légende :</b>", normal_style))
        story.append(Paragraph("• + : Service présent", normal_style))
        story.append(Paragraph("• - : Service absent", normal_style))
        story.append(Paragraph("• T : Service partiellement présent", normal_style))
    
    story.append(Spacer(1, 0.2*inch))
    
    # Ajout de la comparaison des fonctionnalités clés
    story.append(Paragraph("Comparaison des Fonctionnalités Clés", styles['Heading3']))
    if 'marche_comparison_table' in saved_data:
        if isinstance(saved_data['marche_comparison_table'], dict):
            criteres = saved_data['marche_comparison_table'].get('Critères', [])
            
            if criteres:
                # Obtenir tous les noms de concurrents (toutes les colonnes sauf 'Critères')
                concurrents_noms = [col for col in saved_data['marche_comparison_table'].keys() if col != 'Critères']
                
                # Créer l'entête
                header = ["Critères"] + concurrents_noms
                comp_data = [header]
                
                # Ajouter les lignes
                for i, critere in enumerate(criteres):
                    row = [critere]
                    for concurrent in concurrents_noms:
                        values = saved_data['marche_comparison_table'].get(concurrent, [])
                        if i < len(values):
                            row.append(values[i])
                        else:
                            row.append("")
                    comp_data.append(row)
                
                # Créer le tableau
                comp_func_table = create_styled_table(
                    comp_data, 
                    colWidths=[doc.width/(len(header))] * len(header),
                    style_commands=[
                        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                    ]
                )
                story.append(comp_func_table)
            else:
                # Table vide en cas de données manquantes
                default_comp_func_data = [
                    ["Fonctionnalité", "", "", ""],
                    ["", "", "", ""],
                    ["", "", "", ""],
                    ["", "", "", ""]
                ]
                comp_func_table = create_styled_table(
                    default_comp_func_data,
                    colWidths=[doc.width/4.0] * 4,
                    style_commands=[
                        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                    ]
                )
                story.append(comp_func_table)
        else:
            # Table vide en cas de données manquantes
            default_comp_func_data = [
                ["Fonctionnalité", "", "", ""],
                ["", "", "", ""],
                ["", "", "", ""],
                ["", "", "", ""]
            ]
            comp_func_table = create_styled_table(
                default_comp_func_data,
                colWidths=[doc.width/4.0] * 4,
                style_commands=[
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                ]
            )
            story.append(comp_func_table)
    else:
        # Table vide en cas de données manquantes
        default_comp_func_data = [
            ["Fonctionnalité", "", "", ""],
            ["", "", "", ""],
            ["", "", "", ""],
            ["", "", "", ""]
        ]
        comp_func_table = create_styled_table(
            default_comp_func_data,
            colWidths=[doc.width/4.0] * 4,
            style_commands=[
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
            ]
        )
        story.append(comp_func_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Analyse Comparative
    story.append(Paragraph("Analyse Comparative", styles['Heading3']))
    for line in saved_data.get('marche_analyse', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Matrice de Comparaison
    story.append(Paragraph("Matrice de Comparaison", styles['Heading3']))
    
    # Utiliser uniquement les données de marche_matrice_table
    if 'marche_matrice_table' in saved_data:
        if isinstance(saved_data['marche_matrice_table'], dict):
            criteres = saved_data['marche_matrice_table'].get('Critère', [])
            
            if criteres:
                # Obtenir tous les noms de concurrents (toutes les colonnes sauf 'Critère')
                concurrents_mat = [col for col in saved_data['marche_matrice_table'].keys() if col != 'Critère']
                
                # Créer l'entête
                header = ["Critère"] + concurrents_mat
                matrice_data = [header]
                
                # Ajouter les lignes
                for i, critere in enumerate(criteres):
                    row = [critere]
                    for concurrent in concurrents_mat:
                        values = saved_data['marche_matrice_table'].get(concurrent, [])
                        if i < len(values):
                            row.append(values[i])
                        else:
                            row.append("")
                    matrice_data.append(row)
                
                # Créer le tableau
                if len(header) > 0:
                    col_widths = [doc.width/3.0]  # Première colonne plus large
                    if len(header) > 1:
                        col_widths.extend([doc.width/(3.0*(len(header)-1))]*len(concurrents_mat))
                    
                    matrice_table = create_styled_table(
                        matrice_data,
                        colWidths=col_widths,
                        style_commands=[
                            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                            ('LEFTPADDING', (0, 0), (-1, -1), 4),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                            ('TOPPADDING', (0, 0), (-1, -1), 4),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                        ]
                    )
                    story.append(matrice_table)
                else:
                    # Table vide en cas de données manquantes
                    default_matrice_data = [
                        ["Critère", "", "", ""],
                        ["", "", "", ""],
                        ["", "", "", ""],
                        ["", "", "", ""]
                    ]
                    matrice_table = create_styled_table(
                        default_matrice_data,
                        colWidths=[doc.width/2.0, doc.width/6.0, doc.width/6.0, doc.width/6.0],
                        style_commands=[
                            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                            ('LEFTPADDING', (0, 0), (-1, -1), 4),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                            ('TOPPADDING', (0, 0), (-1, -1), 4),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                        ]
                    )
                    story.append(matrice_table)
            else:
                # Table vide en cas de données manquantes
                default_matrice_data = [
                    ["Critère", "", "", ""],
                    ["", "", "", ""],
                    ["", "", "", ""],
                    ["", "", "", ""]
                ]
                matrice_table = create_styled_table(
                    default_matrice_data,
                    colWidths=[doc.width/2.0, doc.width/6.0, doc.width/6.0, doc.width/6.0],
                    style_commands=[
                        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                    ]
                )
                story.append(matrice_table)
        else:
            # Table vide en cas de données manquantes
            default_matrice_data = [
                ["Critère", "", "", ""],
                ["", "", "", ""],
                ["", "", "", ""],
                ["", "", "", ""]
            ]
            matrice_table = create_styled_table(
                default_matrice_data,
                colWidths=[doc.width/2.0, doc.width/6.0, doc.width/6.0, doc.width/6.0],
                style_commands=[
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                ]
            )
            story.append(matrice_table)
    else:
        # Table vide en cas de données manquantes
        default_matrice_data = [
            ["Critère", "", "", ""],
            ["", "", "", ""],
            ["", "", "", ""],
            ["", "", "", ""]
        ]
        matrice_table = create_styled_table(
            default_matrice_data,
            colWidths=[doc.width/2.0, doc.width/6.0, doc.width/6.0, doc.width/6.0],
            style_commands=[
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
            ]
        )
        story.append(matrice_table)

    story.append(Spacer(1, 0.2*inch))
    
    # Business Model Canvas
    story.append(Paragraph("Business Model Canvas", heading2_style))
    
    # Créer une représentation visuelle du BMC selon l'image partagée
    bmc_colors = {
        "partenaires": "#ffadb9",    # Rose
        "activites": "#b388ff",      # Violet
        "proposition": "#81c784",     # Vert
        "relations": "#ffb74d",      # Orange
        "segments": "#4fc3f7",       # Bleu
        "ressources": "#b388ff",     # Violet
        "canaux": "#ffb74d",         # Orange
        "couts": "#ffd54f",          # Jaune
        "revenus": "#b388ff"         # Violet
    }
    
    # Définir les styles pour les titres et le contenu du BMC
    bmc_title_style = ParagraphStyle(
        'BMC_Title',
        parent=styles['Heading3'],
        alignment=TA_CENTER,
        fontSize=12,
        leading=14,
        spaceAfter=6,
        backColor=colors.white,
    )
    
    bmc_content_style = ParagraphStyle(
        'BMC_Content',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        spaceBefore=0,
    )
    
    # Construire le tableau du BMC
    # Première rangée: Partenaires, Activités, Proposition, Relations, Segments
    top_row_data = [
        [
            # Partenaires Clés
            [Paragraph("<b>Partenaires Clés</b>", bmc_title_style)] + 
            [Paragraph(line, bmc_content_style) for line in saved_data.get('bmc_partenaires', '').split('\n') if line.strip()],
            
            # Activités Clés
            [Paragraph("<b>Activités Clés</b>", bmc_title_style)] + 
            [Paragraph(line, bmc_content_style) for line in saved_data.get('bmc_activites', '').split('\n') if line.strip()],
            
            # Proposition de Valeur
            [Paragraph("<b>Proposition de Valeur</b>", bmc_title_style)] + 
            [Paragraph(line, bmc_content_style) for line in saved_data.get('bmc_proposition', '').split('\n') if line.strip()],
            
            # Relations avec les Clients
            [Paragraph("<b>Relations avec les Clients</b>", bmc_title_style)] + 
            [Paragraph(line, bmc_content_style) for line in saved_data.get('bmc_relations', '').split('\n') if line.strip()],
            
            # Segments de Clientèle
            [Paragraph("<b>Segments de Clientèle</b>", bmc_title_style)] + 
            [Paragraph(line, bmc_content_style) for line in saved_data.get('bmc_segments', '').split('\n') if line.strip()],
        ]
    ]
    
    # Deuxième rangée: vide, Ressources, vide, Canaux, vide
    middle_row_data = [
        [
            # Vide (continuation de Partenaires)
            [],
            
            # Ressources Clés
            [Paragraph("<b>Ressources Clés</b>", bmc_title_style)] + 
            [Paragraph(line, bmc_content_style) for line in saved_data.get('bmc_ressources', '').split('\n') if line.strip()],
            
            # Vide (continuation de Proposition)
            [],
            
            # Canaux
            [Paragraph("<b>Canaux</b>", bmc_title_style)] + 
            [Paragraph(line, bmc_content_style) for line in saved_data.get('bmc_canaux', '').split('\n') if line.strip()],
            
            # Vide (continuation de Segments)
            [],
        ]
    ]
    
    # Troisième rangée: Structure de Coûts, vide, vide, vide, Sources de Revenus
    bottom_row_data = [
        [
            # Structure de Coûts (s'étend sur 2 colonnes)
            [Paragraph("<b>Structure de Coûts</b>", bmc_title_style)] + 
            [Paragraph(line, bmc_content_style) for line in saved_data.get('bmc_couts', '').split('\n') if line.strip()],
            
            # Sources de Revenus (s'étend sur 3 colonnes)
            [Paragraph("<b>Sources de Revenus</b>", bmc_title_style)] + 
            [Paragraph(line, bmc_content_style) for line in saved_data.get('bmc_revenus', '').split('\n') if line.strip()],
        ]
    ]
    
    try:
        # Créer les tableaux pour chaque rangée
        top_table = Table(top_row_data, colWidths=[doc.width/5.0]*5)         
        middle_table = Table(middle_row_data, colWidths=[doc.width/5.0]*5)
        bottom_table = Table(bottom_row_data, colWidths=[doc.width/2.0, doc.width/2.0])
        
        # Appliquer le style aux tableaux
        top_table.setStyle(TableStyle([
            # Partenaires Clés
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor(bmc_colors['partenaires'])),
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            
            # Activités Clés
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor(bmc_colors['activites'])),
            ('VALIGN', (1, 0), (1, 0), 'TOP'),
            
            # Proposition de Valeur
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor(bmc_colors['proposition'])),
            ('VALIGN', (2, 0), (2, 0), 'TOP'),
            
            # Relations avec les Clients
            ('BACKGROUND', (3, 0), (3, 0), colors.HexColor(bmc_colors['relations'])),
            ('VALIGN', (3, 0), (3, 0), 'TOP'),
            
            # Segments de Clientèle             # Segments de Clientèle
            ('BACKGROUND', (4, 0), (4, 0), colors.HexColor(bmc_colors['segments'])),
            ('VALIGN', (4, 0), (4, 0), 'TOP'),
            
            ('BOX', (0, 0), (0, 0), 1, colors.black),
            ('BOX', (1, 0), (1, 0), 1, colors.black),
            ('BOX', (2, 0), (2, 0), 1, colors.black),
            ('BOX', (3, 0), (3, 0), 1, colors.black),
            ('BOX', (4, 0), (4, 0), 1, colors.black),
        ]))
        
        middle_table.setStyle(TableStyle([
            # Partenaires Clés (continuation)
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor(bmc_colors['partenaires'])),
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            
            # Ressources Clés
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor(bmc_colors['ressources'])),
            ('VALIGN', (1, 0), (1, 0), 'TOP'),
            
            # Proposition de Valeur (continuation)
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor(bmc_colors['proposition'])),
            ('VALIGN', (2, 0), (2, 0), 'TOP'),
            
            # Canaux
            ('BACKGROUND', (3, 0), (3, 0), colors.HexColor(bmc_colors['canaux'])),
            ('VALIGN', (3, 0), (3, 0), 'TOP'),
            
            # Segments de Clientèle (continuation)
            ('BACKGROUND', (4, 0), (4, 0), colors.HexColor(bmc_colors['segments'])),
            ('VALIGN', (4, 0), (4, 0), 'TOP'),
            
            ('BOX', (1, 0), (1, 0), 1, colors.black),
            ('BOX', (3, 0), (3, 0), 1, colors.black),
        ]))
        
        bottom_table.setStyle(TableStyle([
            # Structure de Coûts
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor(bmc_colors['couts'])),
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            
            # Sources de Revenus
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor(bmc_colors['revenus'])),
            ('VALIGN', (1, 0), (1, 0), 'TOP'),
            
            ('BOX', (0, 0), (0, 0), 1, colors.black),
            ('BOX', (1, 0), (1, 0), 1, colors.black),
        ]))
        
        # Ajouter les tableaux au story
        story.append(top_table)
        story.append(middle_table)
        story.append(bottom_table)
    except Exception as e:
        story.append(Paragraph(f"Erreur lors de la création du Business Model Canvas: {str(e)}", normal_style))
    
    story.append(Spacer(1, 0.2*inch))
    
    # Modèle d'Affaires - Tableaux détaillés
    story.append(Paragraph("Modèle d'Affaires", heading2_style))
    
    # Fonction pour ajouter un tableau de modèle d'affaires de manière sécurisée
    def add_modele_table(story, key, title):
        if key in saved_data:
            story.append(Paragraph(title, styles['Heading3']))
            try:
                if isinstance(saved_data[key], dict) and saved_data[key]:
                    keys = list(saved_data[key].keys())
                    if keys:
                        table_data = [keys]
                        
                        # Déterminer le nombre de lignes
                        n_rows = max([len(val) for val in saved_data[key].values() if isinstance(val, list)]) if saved_data[key] else 0
                        
                        # Ajouter chaque ligne
                        for i in range(n_rows):
                            row = []
                            for k in keys:
                                values = saved_data[key].get(k, [])
                                if isinstance(values, list) and i < len(values):
                                    row.append(values[i])
                                else:
                                    row.append("")
                            table_data.append(row)
                        
                        # Créer le tableau
                        if table_data and len(table_data) > 1:
                            table = create_styled_table(
                                table_data,
                                colWidths=[doc.width/len(keys)] * len(keys),
                                style_commands=[
                                    ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                                ]
                            )
                            story.append(table)
                            story.append(Spacer(1, 0.1*inch))
                        else:
                            story.append(Paragraph("Données insuffisantes pour créer le tableau", normal_style))
                    else:
                        story.append(Paragraph("Aucune colonne définie pour ce tableau", normal_style))
                elif isinstance(saved_data[key], list) and saved_data[key]:
                    # Traiter les données au format liste
                    if saved_data[key][0]:
                        columns = list(saved_data[key][0].keys())
                        table_data = [columns]
                        
                        for item in saved_data[key]:
                            row = []
                            for col in columns:
                                row.append(item.get(col, ""))
                            table_data.append(row)
                        
                        if len(table_data) > 1:
                            table = create_styled_table(
                                table_data,
                                colWidths=[doc.width/len(columns)] * len(columns),
                                style_commands=[
                                    ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
                                ]
                            )
                            story.append(table)
                            story.append(Spacer(1, 0.1*inch))
                        else:
                            story.append(Paragraph("Données insuffisantes pour créer le tableau", normal_style))
                    else:
                        story.append(Paragraph("Données vides pour ce tableau", normal_style))
                else:
                    story.append(Paragraph(f"Format de données non reconnu pour {title}", normal_style))
            except Exception as e:
                story.append(Paragraph(f"Erreur lors de la création du tableau {title}: {str(e)}", normal_style))
                story.append(Spacer(1, 0.1*inch))
    
    # Ajouter tous les tableaux de modèle d'affaires
    add_modele_table(story, 'modele_partenaires', "Partenaires Clés")
    add_modele_table(story, 'modele_activites', "Activités Clés")
    add_modele_table(story, 'modele_proposition', "Proposition de Valeur")
    add_modele_table(story, 'modele_relations', "Relations Clients")
    add_modele_table(story, 'modele_segments', "Segments Clients")
    add_modele_table(story, 'modele_ressources', "Ressources Clés")
    add_modele_table(story, 'modele_couts', "Structure de Coûts")
    add_modele_table(story, 'modele_canaux', "Canaux")
    add_modele_table(story, 'modele_revenus', "Sources de Revenus")
    
    story.append(Spacer(1, 0.2*inch))
    
    # Stratégie Commerciale
    story.append(Paragraph("STRATÉGIE COMMERCIALE", heading1_style))
    
    # Cibles Commerciales
    story.append(Paragraph("1. Cibles Commerciales", heading2_style))
    story.append(Paragraph("Particuliers", styles['Heading3']))
    for line in saved_data.get('part', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    
    # Projections
    if 'projections_table' in saved_data:
        story.append(Spacer(1, 0.1*inch))
        
        if isinstance(saved_data['projections_table'], dict):
            annees = saved_data['projections_table'].get('Année', [])
            visiteurs = saved_data['projections_table'].get('Visiteurs', [])
            ventes = saved_data['projections_table'].get('Ventes', [])
            
            if annees and visiteurs and ventes:
                projections_data = [["Année", "Visiteurs", "Ventes"]]
                for i in range(min(len(annees), len(visiteurs), len(ventes))):
                    projections_data.append([str(annees[i]), visiteurs[i], ventes[i]])
                
                projections_table = create_styled_table(
                    projections_data,
                    colWidths=[doc.width/3.0, doc.width/3.0, doc.width/3.0]
                )
                story.append(projections_table)
            else:
                # Table vide en cas de données manquantes
                default_projections_data = [
                    ["Année", "Visiteurs", "Ventes"],
                    ["", "", ""],
                    ["", "", ""],
                    ["", "", ""]
                ]
                projections_table = create_styled_table(
                    default_projections_data,
                    colWidths=[doc.width/3.0, doc.width/3.0, doc.width/3.0]
                )
                story.append(projections_table)
        else:
            # Table vide en cas de données manquantes
            default_projections_data = [
                ["Année", "Visiteurs", "Ventes"],
                ["", "", ""],
                ["", "", ""],
                ["", "", ""]
            ]
            projections_table = create_styled_table(
                default_projections_data,
                colWidths=[doc.width/3.0, doc.width/3.0, doc.width/3.0]
            )
            story.append(projections_table)
    
    # Associations, Écoles, Entreprises
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Associations", styles['Heading3']))
    for line in saved_data.get('assoc', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Établissements Scolaires", styles['Heading3']))
    for line in saved_data.get('ecoles', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Entreprises", styles['Heading3']))
    for line in saved_data.get('entrep', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Détails Techniques
    story.append(Paragraph(saved_data.get('tech_title_main', "DÉTAILS TECHNIQUES"), heading1_style))
    
    # Étude technique
    story.append(Paragraph(saved_data.get('tech_title_etude', "1. Étude technique du projet"), heading2_style))
    
    # Prototype
    story.append(Paragraph(saved_data.get('tech_title_prototype', "1.1 Prototype"), heading2_style))
    
    # Partie Électronique
    story.append(Paragraph(saved_data.get('tech_title_electronique', "Partie Électronique"), styles['Heading3']))
    for line in saved_data.get('tech_electronique', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Partie Matériaux
    story.append(Paragraph(saved_data.get('tech_title_materiaux', "Partie Étude des Matériaux"), styles['Heading3']))
    for line in saved_data.get('tech_materiaux', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Application Mobile
    story.append(Paragraph(saved_data.get('tech_title_application', "1.2 Application Mobile"), heading2_style))
    for line in saved_data.get('tech_application', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Algorithmes et Traitement des Données
    story.append(Paragraph(saved_data.get('tech_title_algorithmes', "1.3 Algorithmes et Traitement des Données"), heading2_style))
    for line in saved_data.get('tech_algorithmes', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Interface Utilisateur
    story.append(Paragraph(saved_data.get('tech_title_interface', "1.4 Interface Utilisateur et Expérience"), heading2_style))
    for line in saved_data.get('tech_interface', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Tests et Validation
    story.append(Paragraph(saved_data.get('tech_title_tests', "1.5 Tests et Validation"), heading2_style))
    for line in saved_data.get('tech_tests', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Sections originales
    story.append(Paragraph(saved_data.get('tech_title_section2', "2. Prototype"), heading2_style))
    for line in saved_data.get('comp', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph(saved_data.get('tech_title_section3', "3. Application Mobile"), heading2_style))
    for line in saved_data.get('app', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph(saved_data.get('tech_title_section4', "4. Processus de Production"), heading2_style))
    for line in saved_data.get('prod', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Ajouter simplement le pied de page sans les informations du document
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("© Tous droits réservés", 
                          ParagraphStyle(
                              'Footer',
                              parent=styles['Normal'],
                              alignment=TA_CENTER,
                              fontSize=8
                          )))
    
    # Assembler le document (sans la numérotation de pages)
    doc.build(story)
    buffer.seek(0)
    return buffer

st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Aller à :",
    ("Présentation du Projet", "Analyse de Marché", "Stratégie Commerciale", "Détails Techniques")
)

# Bouton de génération PDF dans la barre latérale
if st.sidebar.button("📄 Générer un PDF du rapport"):
    pdf = generate_pdf()
    st.sidebar.download_button(
        label="⬇️ Télécharger le PDF",
        data=pdf,
        file_name="rapport.pdf",
        mime="application/pdf"
    )

# Section pour la gestion des sauvegardes locales
st.sidebar.markdown("---")
st.sidebar.subheader("Mes données")

# Bouton de sauvegarde manuelle - AJOUTÉ
if st.sidebar.button("💾 Sauvegarder mes données"):
    filename = save_data(saved_data)
    if filename:
        st.sidebar.success(f"Données sauvegardées dans {filename}")
    else:
        st.sidebar.error("Erreur lors de la sauvegarde")

# Exporter les données
if st.sidebar.button("⬇️ Exporter ma sauvegarde"):
    # Convertir les données en JSON pour téléchargement
    json_data = json.dumps(st.session_state.user_data, ensure_ascii=False, indent=4)
    
    # Proposer le téléchargement
    st.sidebar.download_button(
        label="📥 Télécharger ma sauvegarde",
        data=json_data,
        file_name="ma_sauvegarde_rapport.json",
        mime="application/json"
    )

# AMÉLIORATION de l'importation des fichiers
uploaded_file = st.sidebar.file_uploader("Importer une sauvegarde", type=['json'], key="file_uploader")
if uploaded_file is not None:
    try:
        # Lire le contenu du fichier
        content = uploaded_file.read().decode('utf-8')
        data = json.loads(content)
        
        # Mettre à jour les données en mémoire
        st.session_state.user_data = data
        saved_data.update(data)  # Aussi mettre à jour saved_data
        
        # Afficher message de succès et bouton pour appliquer les données
        st.sidebar.success("Sauvegarde importée avec succès!")
        
        # Bouton pour appliquer les données (force le rechargement)
        if st.sidebar.button("✅ Appliquer les données importées"):
            try:
                st.rerun()
            except:
                st.sidebar.info("Veuillez rafraîchir la page pour voir les données importées")
                
    except Exception as e:
        st.sidebar.error(f"Erreur lors de l'importation: {str(e)}")

# Bouton pour effacer toutes les données
if st.sidebar.button("🗑️ Réinitialiser mes données"):
    # Afficher une demande de confirmation
    confirmation = st.sidebar.checkbox("Confirmer la réinitialisation")
    if confirmation:
        st.session_state.user_data = {}  # Vider les données
        saved_data.clear()  # Vider les données actuelles
        st.sidebar.success("Données réinitialisées!")
        try:
            st.rerun()
        except:
            st.sidebar.info("Veuillez rafraîchir la page pour voir les changements")

# Page 1: Présentation du Projet
if page == "Présentation du Projet":
    # Ajout d'un input pour changer le titre du projet
    projet_titre = create_input("Titre du Projet", "", "projet_titre")
    
    st.title(projet_titre or "Présentation du Projet")
    
    st.header("1. Description du Projet")
    probleme = create_input("Problématique", "", "pres_prob")
    solution = create_input("Solution proposée", "", "pres_solution", text_area=True)
    
    st.header("2. Fiche d'Identité")
    identite_data = {
        "Information": ["Raison sociale", "Slogan", "Objet social", "Domaines d'activité", 
                       "Siège social", "Forme juridique", "Nombre d'associés", "Valeurs"],
        "Détail": [
            create_input("Raison sociale", "", "ident_rs"),
            create_input("Slogan", "", "ident_slogan"),
            create_input("Objet social", "", "ident_objet_social"),
            create_input("Domaines d'activité", "", "ident_domaines"),
            create_input("Siège social", "", "ident_siege"),
            create_input("Forme juridique", "", "ident_forme"),
            create_input("Nombre d'associés", "", "ident_associes"),
            create_input("Valeurs", "", "ident_valeurs")
        ]
    }
    st.table(pd.DataFrame(identite_data))
    
    st.header("3. Objectifs et Vision")
    objectifs = create_input("Objectifs Principaux", "", "pres_objectifs", text_area=True)
    odd = create_input("Objectifs de Développement Durable", "", "pres_odd", text_area=True)
    mission = create_input("Mission", "", "pres_mission")
    vision = create_input("Vision", "", "pres_vision")
    
    st.header("4. Réalisations Accomplies")
    realisations = create_input("Réalisations", "", "pres_realisations", text_area=True)

# Page 2: Analyse de Marché
elif page == "Analyse de Marché":
    # Ajout d'un input pour changer le titre de la page
    marche_titre = create_input("Titre de la Page", "", "marche_titre")
    st.title(marche_titre or "Analyse de Marché")
    
    st.header("1. Tendances du Marché")
    tendances = create_input("Tendances", "", "marche_tendances", text_area=True)
    
    st.header("2. Cibles Principales")
    cibles_data = {
        "Segment": ["", "", ""],
        "Bénéfices": ["", "", ""]
    }
    create_editable_table(cibles_data, "marche_cibles_table")
    
    st.header("3. Analyse SWOT")
    swot_data = {
        "Catégorie": ["Forces", "Faiblesses", "Opportunités", "Menaces"],
        "Points": ["", "", "", ""]
    }
    create_editable_table(swot_data, "marche_swot_table")
    
    st.header("4. Marketing Mix (4P)")
    marketing_data = {
        "Élément": ["Produit", "Prix", "Distribution", "Promotion"],
        "Stratégie": ["", "", "", ""]
    }
    create_editable_table(marketing_data, "marche_marketing_table")
    
    st.header("5. Analyse Concurrentielle")
    st.subheader("Tableau Comparatif des Concurrents")
    concurrents_data = {
        "Type": [""],
        "Nom": [""],
        "Localisation": [""],
        "Description": [""]
    }
    create_editable_table(concurrents_data, "marche_concurrents_table")
    
    # Ajout du nouveau tableau comparatif détaillé des concurrents avec inputs
    st.markdown("---")
    df, criteres_column_name, concurrents = create_competitor_comparison_table("competitors_comparison_table")
    st.markdown("---")
    
    st.subheader("Comparaison des Fonctionnalités Clés")
    comparison_data = {
        "Critères": ["", "", ""],
        "": ["", "", ""],
        "": ["", "", ""],
        "": ["", "", ""]
    }
    create_editable_table(comparison_data, "marche_comparison_table")
    
    st.subheader("Analyse Comparative")
    analyse_comp = create_input("Analyse", "", "marche_analyse", text_area=True)
    
    st.subheader("Matrice de Comparaison")
    matrice_data = {
        "Critère": ["", "", ""],
        "": ["", "", ""],
        "": ["", "", ""]
    }
    create_editable_table(matrice_data, "marche_matrice_table")
    
    # Ajout du Business Model Canvas avec inputs
    st.markdown("---")
    create_business_model_canvas("bmc")
    st.markdown("---")
    
    st.header("6. Modèle d'Affaires")
    create_expandable_table("Partenaires Clés", 
                          {"Type": [""], "Rôle": [""]}, 
                          "modele_partenaires")
    create_expandable_table("Activités Clés", 
                          {"Activité": [""], "Description": [""]}, 
                          "modele_activites")
    create_expandable_table("Proposition de Valeur", 
                          {"Élément": [""], "Description": [""]}, 
                          "modele_proposition")
    create_expandable_table("Relations Clients", 
                          {"Type": [""], "Description": [""]}, 
                          "modele_relations")
    create_expandable_table("Segments Clients", 
                          {"Segment": [""], "Description": [""]}, 
                          "modele_segments")
    create_expandable_table("Ressources Clés", 
                          {"Type": [""], "Description": [""]}, 
                          "modele_ressources")
    create_expandable_table("Structure de Coûts", 
                          {"Poste": [""], "Description": [""]}, 
                          "modele_couts")
    create_expandable_table("Canaux", 
                          {"Canal": [""], "Description": [""]}, 
                          "modele_canaux")
    create_expandable_table("Sources de Revenus", 
                          {"Source": [""], "Description": [""]}, 
                          "modele_revenus")

# Page 3: Stratégie Commerciale
elif page == "Stratégie Commerciale":
    # Ajout d'un input pour changer le titre de la page
    strategie_titre = create_input("Titre de la Page", "", "strategie_titre")
    st.title(strategie_titre or "Stratégie Commerciale")
    
    st.header("1. Cibles Commerciales")
    st.subheader("Particuliers")
    particuliers = create_input("Stratégie", "", "part", text_area=True)
    
    annees = st.slider("Nombre d'années", 1, 5, 3, key="annees_slider")
    projections = {
        "Année": list(range(1, annees+1)),
        "Visiteurs": [create_input(f"Visiteurs {i}", "", f"vis{i}") for i in range(1, annees+1)],
        "Ventes": [create_input(f"Ventes {i}", "", f"ventes{i}") for i in range(1, annees+1)]
    }
    create_editable_table(projections, "projections_table")
    
    st.subheader("Associations")
    associations = create_input("Plan associations", "", "assoc", text_area=True)
    
    st.subheader("Établissements Scolaires")
    ecoles = create_input("Plan écoles", "", "ecoles", text_area=True)
    
    st.subheader("Entreprises")
    entreprises = create_input("Plan entreprises", "", "entrep", text_area=True)

# Page 4: Détails Techniques
elif page == "Détails Techniques":
    # Ajout d'un input pour changer le titre de la page
    technique_titre = create_input("Titre de la Page", "", "technique_titre")
    st.title(technique_titre or "Détails Techniques")
    
    # Nouvelle section pour l'étude technique - Avec titre modifiable
    tech_title_main = create_input("Titre principal", "", "tech_title_main")
    tech_title_etude = create_input("Titre étude technique", "", "tech_title_etude")
    st.header(tech_title_etude or "1. Étude technique du projet")
    
    # Section prototype - Avec titre modifiable
    tech_title_prototype = create_input("Titre prototype", "", "tech_title_prototype")
    st.subheader(tech_title_prototype or "1.1 Prototype")
    
    # Partie électronique - Avec titre modifiable
    tech_title_electronique = create_input("Titre partie électronique", "", "tech_title_electronique")
    st.markdown(f"##### {tech_title_electronique or 'Partie Électronique'}")
    partie_electronique = create_input("", "", "tech_electronique", text_area=True, height=300)
    
    # Partie étude des matériaux - Avec titre modifiable
    tech_title_materiaux = create_input("Titre partie matériaux", "", "tech_title_materiaux")
    st.markdown(f"##### {tech_title_materiaux or 'Partie Étude des Matériaux'}")
    partie_materiaux = create_input("", "", "tech_materiaux", text_area=True, height=250)
    
    # Section application mobile - Avec titre modifiable
    tech_title_application = create_input("Titre application mobile", "", "tech_title_application")
    st.subheader(tech_title_application or "1.2 Application Mobile")
    partie_application = create_input("", "", "tech_application", text_area=True, height=250)
    
    # Section algorithmes et traitement des données - Avec titre modifiable
    tech_title_algorithmes = create_input("Titre algorithmes", "", "tech_title_algorithmes")
    st.subheader(tech_title_algorithmes or "1.3 Algorithmes et Traitement des Données")
    partie_algorithmes = create_input("", "", "tech_algorithmes", text_area=True, height=200)
    
    # Section interface utilisateur et expérience - Avec titre modifiable
    tech_title_interface = create_input("Titre interface utilisateur", "", "tech_title_interface")
    st.subheader(tech_title_interface or "1.4 Interface Utilisateur et Expérience")
    partie_interface = create_input("", "", "tech_interface", text_area=True, height=200)
    
    # Section tests et validation - Avec titre modifiable
    tech_title_tests = create_input("Titre tests et validation", "", "tech_title_tests")
    st.subheader(tech_title_tests or "1.5 Tests et Validation")
    partie_tests = create_input("", "", "tech_tests", text_area=True, height=200)
    
    # Garde les sections prototype et application originales - Avec titres modifiables
    tech_title_section2 = create_input("Titre section 2", "", "tech_title_section2")
    st.header(tech_title_section2 or "2. Prototype")
    composants = create_input("Composants", "", "comp", text_area=True)
    
    tech_title_section3 = create_input("Titre section 3", "", "tech_title_section3")
    st.header(tech_title_section3 or "3. Application Mobile")
    app_mobile = create_input("App mobile", "", "app", text_area=True)
    
    tech_title_section4 = create_input("Titre section 4", "", "tech_title_section4")
    st.header(tech_title_section4 or "4. Processus de Production")
    production = create_input("Production", "", "prod", text_area=True)

# Pied de page
st.markdown("---")
st.markdown(f"Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
