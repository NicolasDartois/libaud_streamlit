import streamlit as st
import pandas as pd
import os
import requests

# === Fonctions de conversion ===
def convertir_en_mm(valeur, unite):
    try: valeur = float(valeur)
    except: return '', 'Millimètre'
    return round(valeur * {'MMT':1, 'CMT':10, 'DMT':100, 'MTR':1000}.get(unite.strip().upper(), 0), 2), 'Millimètre'

def convertir_en_kg(valeur, unite):
    try: valeur = float(valeur)
    except: return '', 'Kilogramme'
    return round(valeur * {'GRM':0.001, 'KGM':1}.get(unite.strip().upper(), 0), 3), 'Kilogramme'

def convertir_en_m3(valeur, unite):
    try: valeur = float(valeur)
    except: return '', 'mètre cube'
    return round(valeur * {'CTQ':1e-6, 'DMQ':1e-3, 'MTQ':1}.get(unite.strip().upper(), 0), 6), 'mètre cube'

# === Interface Streamlit ===
st.title("Traitement des données produits - Version GitHub")

# Charger le fichier de correspondance depuis le repo GitHub
df_codes = pd.read_csv("https://raw.githubusercontent.com/<TON-REPO-GITHUB>/main/data/code.csv")

fournisseurs_disponibles = df_codes['FOURNISSEUR'].unique().tolist()
fournisseur_selectionne = st.selectbox("Choisir un fournisseur", options=fournisseurs_disponibles)

fabdis_file = st.file_uploader("Fichier FABDIS (.xlsx)", type="xlsx")
dossier_sortie = st.text_input("Dossier de sortie (visuels, data.xlsx)", value="./output")

if st.button("Lancer le traitement"):
    try:
        df_refs = df_codes[df_codes['FOURNISSEUR'] == fournisseur_selectionne].rename(columns={
            'CODE LIBAUD': 'LIBAUD',
            'CODE FOURNISSEUR': 'FOURNISSEUR'
        })

        if fabdis_file is None:
            st.error("Veuillez uploader un fichier FABDIS valide.")
            st.stop()

        # === Lecture des onglets FABDIS ===
        df_media = pd.read_excel(fabdis_file, sheet_name='B03_MEDIA', dtype=str).fillna('')
        df_logistique = pd.read_excel(fabdis_file, sheet_name='B02_LOGISTIQUE', dtype=str).fillna('')
        df_logistique['QC'] = pd.to_numeric(df_logistique['QC'], errors='coerce')

        folder_visuels = os.path.join(dossier_sortie, "Visuels")
        os.makedirs(folder_visuels, exist_ok=True)
        data_output_path = os.path.join(dossier_sortie, "data.xlsx")

        # === Téléchargement des images ===
        for _, row in df_refs.iterrows():
            ref_libaud = row['LIBAUD']
            ref_fournisseur = row['FOURNISSEUR']
            image_path = os.path.join(folder_visuels, f"{ref_libaud}.png")

            if os.path.exists(image_path):
                continue

            df_image = df_media[(df_media['REFCIALE'] == ref_fournisseur) & (df_media['MTYP'] == 'PHOTO')]
            if not df_image.empty:
                url = df_image.iloc[0]['MURLT']
                if url:
                    try:
                        resp = requests.get(url, timeout=10)
                        resp.raise_for_status()
                        with open(image_path, 'wb') as f:
                            f.write(resp.content)
                    except:
                        pass

        # === Traitement logistique ===
        data_rows = []
        for _, row in df_refs.iterrows():
            code_libaud = row['LIBAUD']
            code_fournisseur = row['FOURNISSEUR']
            df_lignes = df_logistique[df_logistique['REFCIALE'] == code_fournisseur]

            if df_lignes.empty:
                continue

            ligne_min = df_lignes.loc[df_lignes['QC'].idxmin()]
            ligne_max = df_lignes.loc[df_lignes['QC'].idxmax()]

            haut, haut_u = convertir_en_mm(ligne_min.get('HAUT', ''), ligne_min.get('HAUTU', ''))
            larg, larg_u = convertir_en_mm(ligne_min.get('LARG', ''), ligne_min.get('LARGU', ''))
            prof, prof_u = convertir_en_mm(ligne_min.get('PROF', ''), ligne_min.get('PROFU', ''))
            poids, poids_u = convertir_en_kg(ligne_min.get('POIDS', ''), ligne_min.get('POIDSU', ''))
            vol, vol_u = convertir_en_m3(ligne_min.get('VOL', ''), ligne_min.get('VOLU', ''))

            hautc, hautc_u = convertir_en_mm(ligne_max.get('HAUT', ''), ligne_max.get('HAUTU', ''))
            largc, largc_u = convertir_en_mm(ligne_max.get('LARG', ''), ligne_max.get('LARGU', ''))
            profc, profc_u = convertir_en_mm(ligne_max.get('PROF', ''), ligne_max.get('PROFU', ''))

            data_rows.append({
                'Code libaud': code_libaud,
                'Code fournisseur': code_fournisseur,
                'Poids': poids,
                'Unité de poids': poids_u,
                'volume': vol,
                'unité de volume': vol_u,
                'hauteur': haut,
                'unité de hauteur': haut_u,
                'largeur': larg,
                'unité de largeur': larg_u,
                'profondeur': prof,
                'unité de profondeur': prof_u,
                'hauteur conditionnement': hautc,
                'unité de hauteur conditionnement': hautc_u,
                'largeur conditionnement': largc,
                'unité de largeur conditionnement': largc_u,
                'profondeur conditionnement': profc,
                'unité de profondeur conditionnement': profc_u,
                'unité du plus petit conditionnement': ligne_min.get('QCT', ''),
                'quantité pour le plus petit conditionnement': ligne_min.get('QC', ''),
                'unité du plus grand conditionnement': ligne_max.get('QCT', ''),
                'quantité pour le plus grand conditionnement': ligne_max.get('QC', ''),
            })

        df_data = pd.DataFrame(data_rows)
        df_data.to_excel(data_output_path, index=False)

        st.success(f"Export terminé : {data_output_path}")
        st.dataframe(df_data.head())

    except Exception as e:
        st.error(f"Erreur : {e}")
