# ⚡ WiFiTIC

[![Release](https://img.shields.io/github/v/release/AuroreVgn/wifiTIC?label=release&style=flat-square)](https://github.com/AuroreVgn/wifiTIC/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Intégration-41BDF5?style=flat-square&logo=homeassistant)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square)](https://www.hacs.xyz/)
[![Mainteneur](https://img.shields.io/badge/mainteneur-%40AuroreVgn-0078D7?style=flat-square)](https://github.com/AuroreVgn)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Soutenir-FF5E5B?logo=kofi&logoColor=white&style=flat-square)](https://ko-fi.com/aurorevgn)

Intégration personnalisée **Home Assistant** pour les compteurs **Linky** équipés du module **WiFiTIC de CARTELECTRONIC**. Elle associe les mesures en temps réel reçues par **MQTT** et les informations **REST** du module pour suivre le soutirage, l'injection réseau, les index tarifaires et l'historique énergétique.

> [!IMPORTANT]
> Projet communautaire non officiel, indépendant de CARTELECTRONIC, d'Enedis et de Home Assistant. Les données électriques sont fournies par le compteur et son module WiFiTIC.

## 🏠 Mes projets Home Assistant

[Découvrir mes projets Home Assistant](https://gentle-suggestion-7c3.notion.site/Mes-projets-Home-Assistant-3eda02eefa8f81a48621c3caeef7fa8e)

## ☕ Soutenir le projet

Si cette intégration vous est utile, vous pouvez [soutenir son développement sur Ko-fi](https://ko-fi.com/aurorevgn).

## ✨ Fonctionnalités

- Réception des trames de téléinformation **MQTT**.
- Lecture de la puissance apparente soutirée, du courant et de la tension.
- Estimation de la puissance soutirée en watts à partir de la puissance apparente.
- Mesure de la **puissance injectée** vers le réseau.
- Suivi de l'**index cumulé d'injection** et des **index de consommation par période tarifaire**.
- Affichage des périodes tarifaires et des informations du contrat.
- Suivi des énergies soutirée et injectée « aujourd'hui ».
- Diagnostics du module WiFiTIC, dont les erreurs CRC.
- Importation de l'historique REST vers les statistiques natives MQTT pour compléter le tableau de bord Énergie.
- Traductions française et anglaise.

## 🛡️ Compatibilité et prérequis

- Home Assistant avec l'intégration **MQTT** opérationnelle.
- Un compteur Linky équipé d'un module **WiFiTIC CARTELECTRONIC** accessible depuis Home Assistant.
- Un accès HTTP à l'API REST du module pour la configuration et les données historiques.
- Un module WiFiTIC configuré pour publier les trames sur le broker MQTT.

Le sujet MQTT racine par défaut dans le code est `/wifitic`. Il peut être modifié dans l'assistant de configuration.

> [!NOTE]
> Le nombre et le nom des index tarifaires dépendent du contrat et des informations remontées par le module. Le code prévoit notamment plusieurs index pour les contrats à périodes multiples.

## 📦 Installation

> [!WARNING]
> Le dépôt GitHub contient actuellement la documentation. **Les fichiers de l'intégration ne sont pas encore publiés dans le dépôt** : les instructions HACS ci-dessous ne seront utilisables qu'après leur mise en ligne.

### Option A — HACS (après publication du code)

[![Ajouter le dépôt dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=AuroreVgn&repository=wifiTIC&category=integration)

1. Ouvrir **HACS** → **⋮** → **Dépôts personnalisés**.
2. Ajouter `https://github.com/AuroreVgn/wifiTIC`.
3. Choisir **Intégration**, puis installer WiFiTIC.
4. Redémarrer Home Assistant.

### Option B — Installation manuelle

Copier le dossier `custom_components/wifitic` dans `/config/custom_components/wifitic`, puis redémarrer Home Assistant.

## ⚙️ Configuration

Dans Home Assistant : **Paramètres → Appareils et services → Ajouter une intégration → WiFiTIC**.

L'assistant demande :

| Paramètre | Description |
| --- | --- |
| Hôte | Adresse du module WiFiTIC pour l'API REST |
| Identifiant | Facultatif selon la configuration du module |
| Mot de passe | Facultatif selon la configuration du module |
| Sujet MQTT racine | Sujet de publication des trames, `/wifitic` par défaut |

La configuration interroge l'API REST du module et utilise l'identifiant du compteur, lorsqu'il est disponible, pour éviter de configurer deux fois le même équipement.

## 📊 Entités créées

### Mesures électriques

| Capteur | Origine | Unité |
| --- | --- | --- |
| Puissance apparente soutirée | MQTT | VA |
| Puissance soutirée du réseau (estimée) | MQTT | W |
| Intensité instantanée | MQTT | A |
| Tension réseau | MQTT | V |
| Puissance injectée sur le réseau | MQTT | W |
| Index énergie injectée au réseau | MQTT | Wh |
| Index de consommation par période tarifaire | MQTT | Wh |
| Énergie soutirée aujourd'hui | MQTT | Wh |
| Énergie injectée aujourd'hui | MQTT | Wh |

La puissance soutirée en watts est une **estimation** fondée sur la puissance apparente ; elle ne remplace pas une mesure active directe du compteur.

### Contrat, périodes tarifaires et diagnostic

| Capteur | Rôle |
| --- | --- |
| Période tarifaire | Période en cours indiquée par le compteur |
| Profil tarifaire fournisseur aujourd'hui | Information fournisseur remontée par la téléinformation |
| Profil tarifaire fournisseur demain | Information fournisseur lorsqu'elle est disponible |
| État de la téléinformation | État communiqué par le compteur |
| Puissance souscrite | Puissance associée au contrat |
| Seuil de coupure Linky | Seuil remonté par le compteur |
| Contrat | Nom du contrat déterminé à partir des informations REST |
| Trames TIC valides | Diagnostic REST |
| Erreurs de transmission TIC (CRC) | Diagnostic REST |

L'intégration comporte également des entités de diagnostic et un bouton ; leur disponibilité dépend des informations renvoyées par le module.

## ⚡ Tableau de bord Énergie

Les index cumulés d'énergie utilisent des unités d'énergie et une classe d'état adaptées aux statistiques de longue durée de Home Assistant.

- **Soutirage :** sélectionner les index de consommation correspondant aux périodes tarifaires.
- **Injection :** sélectionner l'index d'énergie injectée vers le réseau.

> [!IMPORTANT]
> **Injection réseau ≠ production solaire totale.** L'injection mesure uniquement l'énergie exportée vers le réseau. Une installation photovoltaïque avec autoconsommation ou batterie peut produire davantage que ce qui est injecté.

Dans le graphique Énergie, l'injection apparaît normalement sous l'axe zéro.

## 🕰️ Importation de l'historique REST

L'intégration peut raccorder des données historiques REST aux statistiques natives des capteurs MQTT, pour l'injection et le soutirage.

### 1. Prévisualiser l'historique

```yaml
action: wifitic.preview_history
data:
  start_date: "2026-10-05"
  end_date: "2026-10-08"
```

Cette action analyse l'historique sans modifier Recorder.

### 2. Préparer une fusion native

```yaml
action: wifitic.merge_native_energy_history
data:
  start_date: "2026-10-05"
  end_date: "2026-10-08"
  include_injection: true
  include_consumption: true
  confirm_write: false
```

Les options `include_injection` et `include_consumption` permettent de traiter les deux types d'énergie ensemble ou séparément.

### 3. Confirmer l'importation

Après avoir vérifié les séries et les montants proposés, effectuer une sauvegarde de Recorder, puis relancer avec `confirm_write: true`.

> [!CAUTION]
> La modification des statistiques Recorder est **non atomique**. Une interruption peut laisser une migration partielle. Ne relancez pas aveuglément une importation ayant échoué ou portant sur des dates déjà migrées. Les statistiques existantes doivent être contrôlées avant toute nouvelle écriture.

### Comment fonctionne le raccordement ?

Les données historiques sont converties en Wh et alignées sur les heures de statistiques de Home Assistant. Le raccordement tient compte de la première période MQTT et du cumul initial de Recorder, qui n'est pas nécessairement égal à zéro.

L'objectif est de prolonger l'historique des mêmes capteurs, sans créer une seconde source d'énergie dans le tableau de bord.

## 🧩 Carte Lovelace

Une carte dédiée est prévue dans le dépôt **[WiFiTIC Card](https://github.com/AuroreVgn/wifiTIC_card)**.

## ℹ️ Fonctionnement et limites

- Les mesures temps réel dépendent des trames MQTT reçues.
- Les informations de contrat et certains diagnostics proviennent de REST.
- Les données historiques disponibles dépendent de la conservation assurée par le module WiFiTIC.
- Les index historiques et MQTT ne doivent pas se chevaucher.
- La migration native ne remplace pas une sauvegarde Recorder.
- Le code de la version initiale `0.0.1` doit encore être publié sur GitHub.

## 🤝 Signaler un problème

Ouvrir une [issue GitHub](https://github.com/AuroreVgn/wifiTIC/issues) avec la version de Home Assistant, la version de WiFiTIC, le résultat de l'action concernée et les journaux utiles, **sans identifiants ni données personnelles**.

## 📄 Licence

Licence à définir avant publication du code. Aucun fichier `LICENSE` n'est encore publié.
