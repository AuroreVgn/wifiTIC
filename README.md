# 📊 WiFiTIC

[![Release](https://img.shields.io/github/v/release/AuroreVgn/edf-zen-flex?label=release&style=flat-square)](https://github.com/AuroreVgn/wifiTIC/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square)](https://www.hacs.xyz/)
[![Maintainer](https://img.shields.io/badge/maintainer-%40AuroreVgn-0078D7?style=flat-square)](https://github.com/AuroreVgn)
[![Ko--fi](https://img.shields.io/badge/Ko--fi-Soutenir-FF5E5B?logo=kofi&logoColor=white&style=flat-square)](https://ko-fi.com/aurorevgn)

Intégration personnalisée **Home Assistant** pour les compteurs **Linky** équipés du module **WiFiTIC CARTELECTRONIC** : suivi de la consommation, de l'injection réseau, des index tarifaires et de l'historique REST.

> [!IMPORTANT]
> Projet communautaire non officiel, indépendant de CARTELECTRONIC et d'Enedis. Les index d'injection correspondent à l'export réseau et non à la production solaire totale.

## 🏠 Mes projets Home Assistant

[Découvrir mes projets Home Assistant](https://erra.me)

## ☕ Soutenir le projet

Si cette intégration vous est utile, vous pouvez [soutenir son développement sur Ko-fi](https://ko-fi.com/aurorevgn).

## ✨ Fonctionnalités

- Réception des données de téléinformation **MQTT** du compteur Linky.
- Suivi de la consommation et de l'injection réseau.
- Index cumulés par période tarifaire, notamment pour **EDF Zen Flex**.
- Consultation des historiques disponibles via l'API REST du module.
- Prévisualisation des historiques sans écriture.
- Raccordement de l'historique REST aux statistiques énergétiques natives MQTT.
- Compatibilité avec le tableau de bord **Énergie**.
- Carte Lovelace dédiée dans un [dépôt séparé](https://github.com/AuroreVgn/wifiTIC_card).

## 📦 Installation

### Option A — HACS (recommandé)

#### Automatiquement

[![Ouvrir Home Assistant et ajouter ce dépôt dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=AuroreVgn&repository=wifiTIC&category=integration)

#### Manuellement

Cette intégration étant un dépôt personnalisé, il faut l'ajouter une première fois dans HACS :

1. Ouvrir **HACS** → **Intégrations**.
2. Ouvrir le menu **⋮** → **Dépôts personnalisés**.
3. Ajouter :

   ```text
   https://github.com/AuroreVgn/wifiTIC
   ```

4. Choisir la catégorie **Intégration**.
5. Rechercher **WiFiTIC** dans HACS puis installer l'intégration.
6. Redémarrer Home Assistant.

### Option B — Installation manuelle

1. Télécharger la dernière version du dépôt.
2. Copier le dossier :

   ```text
   custom_components/wifitic
   ```

   dans :

   ```text
   /config/custom_components/wifitic
   ```

3. Redémarrer Home Assistant.

Après l'installation, aller dans **Paramètres → Appareils et services → Ajouter une intégration**, puis rechercher **WiFiTIC**.

## ⚙️ Configuration

L'intégration nécessite un module WiFiTIC accessible sur le réseau local et un broker MQTT opérationnel.

### 1. Connexion au module

Renseigner l'adresse du module WiFiTIC et les informations de connexion REST éventuellement nécessaires.

### 2. Téléinformation MQTT

Configurer le module pour publier ses trames sur le broker MQTT. Les sujets de référence sont `/wifitic/teleinfo` et `/wifitic/online` ; ils dépendent du sujet racine configuré.

### 3. Historique énergétique

L'importation de l'historique REST est facultative et distincte de la collecte MQTT en temps réel. Une sauvegarde de Recorder est recommandée avant toute fusion.

## 📊 Entités créées

### Consommation et injection

| Capteur | Rôle |
| --- | --- |
| Index de consommation par période tarifaire | Énergie cumulée soutirée |
| Index d'injection | Énergie cumulée exportée vers le réseau |
| Puissance soutirée | Suivi instantané du soutirage |
| Puissance injectée | Suivi instantané de l'injection |

Les index cumulés peuvent être utilisés dans le tableau de bord **Énergie** de Home Assistant.

### Contrat et période courante

| Donnée | Rôle |
| --- | --- |
| Période tarifaire | Période active remontée par le compteur |
| Contrat | Informations tarifaires disponibles |
| Mesures électriques | Données instantanées issues de la téléinformation |

Le nombre d'index dépend du contrat électrique et des informations publiées par le module.

### Diagnostics

Les données de diagnostic disponibles dépendent de l'état du module WiFiTIC et des informations transmises via MQTT ou REST.

## 🕰️ Importation de l'historique énergétique

Le service `wifitic.preview_history` permet de consulter les séries historiques sans écriture.

Pour prévisualiser la fusion de l'historique d'injection et de soutirage :

```yaml
action: wifitic.merge_native_energy_history
data:
  start_date: "2026-10-05"
  end_date: "2026-10-08"
  include_injection: true
  include_consumption: true
  confirm_write: false
```

Après vérification des données et sauvegarde de Recorder, relancer avec `confirm_write: true` pour écrire les statistiques.

> [!CAUTION]
> Les écritures de statistiques Recorder ne sont pas atomiques. Après une erreur, contrôler les données déjà importées avant toute nouvelle tentative.

## 🧩 Carte Lovelace

La carte est distribuée dans un dépôt distinct : **[WiFiTIC Card](https://github.com/AuroreVgn/wifiTIC_card)**.

Elle permet de présenter les informations WiFiTIC dans un tableau de bord Home Assistant. Consulter son dépôt pour connaître son état de publication.

## ℹ️ Fonctionnement et limites

- La réception des données en temps réel dépend du broker MQTT.
- Les historiques disponibles dépendent de ce que le module WiFiTIC conserve.
- Les index et périodes tarifaires varient selon le contrat.
- L'injection réseau ne représente pas la production photovoltaïque totale.
- Les périodes déjà présentes dans Recorder ne doivent pas être importées une seconde fois.
- Une sauvegarde est indispensable avant une migration de statistiques.

## 🤝 Signaler un problème

Ouvrir une [issue GitHub](https://github.com/AuroreVgn/wifiTIC/issues) en indiquant la version de Home Assistant, la version de l'intégration, le comportement attendu et les journaux utiles **sans données personnelles**.

## 📄 Licence

La licence sera précisée lors de la publication du fichier `LICENSE`.

---

**WiFiTIC** est un projet indépendant, développé pour la communauté Home Assistant.
