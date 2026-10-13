# ⚡ WiFiTIC

[![Release](https://img.shields.io/github/v/release/AuroreVgn/wifiTIC?label=release&style=flat-square)](https://github.com/AuroreVgn/wifiTIC/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-41BDF5?style=flat-square&logo=homeassistant)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Dépôt%20personnalisé-41BDF5?style=flat-square)](https://www.hacs.xyz/)
[![Mainteneur](https://img.shields.io/badge/mainteneur-%40AuroreVgn-0078D7?style=flat-square)](https://github.com/AuroreVgn)
[![Ko--fi](https://img.shields.io/badge/Ko--fi-Soutenir-FF5E5B?logo=kofi&logoColor=white&style=flat-square)](https://ko-fi.com/aurorevgn)

Intégration personnalisée **Home Assistant** pour les compteurs **Linky** équipés d’un module **WiFiTIC CARTELECTRONIC**. Elle permet de suivre les mesures MQTT, les index tarifaires, le soutirage et l’injection réseau, et de raccorder l’historique REST aux statistiques énergétiques natives.

> [!IMPORTANT]
> Projet communautaire non officiel, indépendant de CARTELECTRONIC, d’Enedis et de Home Assistant.

## 🏠 Mes projets Home Assistant

[Découvrir mes projets Home Assistant](https://gentle-suggestion-7c3.notion.site/Mes-projets-Home-Assistant-3eda02eefa8f81a48621c3caeef7fa8e)

## ☕ Soutenir le projet

Si ce projet vous est utile, vous pouvez [soutenir son développement sur Ko-fi](https://ko-fi.com/aurorevgn).

## ✨ Fonctionnalités

- Réception des informations du compteur Linky via **MQTT**.
- Suivi de la puissance instantanée et des index de consommation.
- Mesure de l'énergie **soutirée du réseau** et **injectée vers le réseau**.
- Distinction des périodes tarifaires disponibles dans les données WiFiTIC.
- Importation des historiques REST et raccordement aux statistiques natives MQTT.
- Exploitation des index dans le tableau de bord **Énergie** de Home Assistant.
- Traductions **française et anglaise** de l'interface.

## 🛡️ Compatibilité

L'intégration nécessite un module WiFiTIC CARTELECTRONIC configuré pour publier les données de téléinformation sur un broker MQTT accessible depuis Home Assistant.

> [!NOTE]
> L'injection réseau correspond à l'énergie renvoyée vers le réseau électrique ; elle ne doit pas être confondue avec la production totale d'une installation photovoltaïque.

## 📦 Installation

> [!WARNING]
> **Publication en cours :** le dépôt GitHub contient actuellement sa documentation, mais pas encore le code de l'intégration. Ne tentez pas son installation depuis HACS tant que les fichiers n'ont pas été publiés.

### Option A — HACS (après publication du code)

[![Ouvrir le dépôt dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=AuroreVgn&repository=wifiTIC&category=integration)

1. Dans **HACS**, ouvrir le menu **⋮** puis **Dépôts personnalisés**.
2. Ajouter `https://github.com/AuroreVgn/wifiTIC` dans la catégorie **Intégration**.
3. Installer WiFiTIC et redémarrer Home Assistant.

### Option B — Installation manuelle (après publication du code)

Copier `custom_components/wifitic` dans `/config/custom_components/wifitic`, puis redémarrer Home Assistant.

## ⚙️ Configuration

Ajouter l'intégration depuis **Paramètres → Appareils et services → Ajouter une intégration → WiFiTIC**.

Le module WiFiTIC doit publier ses mesures sur MQTT. La configuration exacte du broker, des identifiants et des sujets dépend de l'installation du compteur.

## 📊 Données et statistiques

| Donnée | Utilisation |
| --- | --- |
| Puissance instantanée | Suivi du soutirage en temps réel |
| Index de consommation | Énergie soutirée, ventilée par période tarifaire |
| Index d'injection | Énergie renvoyée vers le réseau |
| Historique REST | Complément des statistiques énergétiques antérieures au suivi MQTT |

Les index natifs peuvent être sélectionnés dans le **tableau de bord Énergie** de Home Assistant.

## 🕰️ Importation de l'historique

Le service `wifitic.preview_history` permet d'examiner les données historiques sans écriture.

Le service `wifitic.merge_native_energy_history` permet de préparer puis d'effectuer le raccordement des historiques d'injection et de soutirage aux statistiques natives.

Exemple de prévisualisation de la fusion :

```yaml
action: wifitic.merge_native_energy_history
data:
  start_date: "2026-10-05"
  end_date: "2026-10-08"
  include_injection: true
  include_consumption: true
  confirm_write: false
```

> [!CAUTION]
> Une écriture de statistiques historiques peut être difficile à annuler. Examiner le résultat avec `confirm_write: false` et sauvegarder la base Recorder avant toute importation. Éviter de réimporter une période déjà fusionnée.

## 🧩 Carte Lovelace

Une carte dédiée est prévue dans le dépôt [WiFiTIC Card](https://github.com/AuroreVgn/wifiTIC_card).

## ℹ️ Fonctionnement et limites

- Les données disponibles dépendent de la configuration du compteur et du module WiFiTIC.
- Les statistiques historiques et MQTT doivent être raccordées sans chevauchement.
- Le suivi de l'injection ne remplace pas la mesure de production photovoltaïque.
- Le code de la version initiale `0.0.1` n'est pas encore publié dans ce dépôt.

## 🤝 Signaler un problème

Ouvrir une [issue GitHub](https://github.com/AuroreVgn/wifiTIC/issues) en indiquant la version de Home Assistant, les étapes de reproduction et les journaux utiles **sans identifiants ni données personnelles**.

## 📄 Licence

Licence à définir avant publication du code. Aucun fichier LICENSE n'est actuellement publié.
