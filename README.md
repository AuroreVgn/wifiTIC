# 📊 WiFiTIC

[![Release](https://img.shields.io/github/v/release/AuroreVgn/wifiTIC?label=release&style=flat-square)](https://github.com/AuroreVgn/wifiTIC/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square)](https://www.hacs.xyz/)
[![Maintainer](https://img.shields.io/badge/maintainer-%40AuroreVgn-0078D7?style=flat-square)](https://github.com/AuroreVgn)
[![Ko--fi](https://img.shields.io/badge/Ko--fi-Soutenir-FF5E5B?logo=kofi&logoColor=white&style=flat-square)](https://ko-fi.com/aurorevgn)

Intégration personnalisée **Home Assistant** pour les compteurs **Linky** équipés du module **[WiFiTIC de Cartelectronic](https://cartelectronic.fr/accueil/136-wifitic.html)** : suivi de la consommation, de l'injection réseau, des index tarifaires et de l'historique REST.

> [!IMPORTANT]
> Projet communautaire non officiel, indépendant de [Cartelectronic](https://cartelectronic.fr/accueil/136-wifitic.html) et d'Enedis. Les index d'injection correspondent à l'export réseau et non à la production solaire totale.

## 🏠 Mes projets Home Assistant

[Découvrir mes projets Home Assistant](https://erra.me)

## ☕ Soutenir le projet

Si cette intégration vous est utile, vous pouvez [soutenir son développement sur Ko-fi](https://ko-fi.com/aurorevgn).

## ✨ Fonctionnalités

- Configuration depuis l'interface Home Assistant, sans capteurs YAML à créer manuellement.
- **MQTT en temps réel** : puissance apparente soutirée, puissance soutirée estimée, intensité, tension, puissance injectée, index de consommation et d'injection, période tarifaire et informations fournisseur.
- **REST local** : nom du contrat, libellés des périodes tarifaires, informations du compteur et diagnostics de transmission TIC.
- **Index dynamiques** : récupération des libellés de périodes depuis le module ; prise en charge des contrats à plusieurs périodes, notamment **EDF Zen Flex** (code contrat `11`), **Tempo** et des contrats personnalisés.
- Pour **Zen Flex**, adaptation des libellés « pointe » en « sobriété » dans les index.
- **Huit relais Linky R1 à R8**, exposés comme capteurs binaires de diagnostic, désactivés par défaut.
- **Énergie soutirée et injectée aujourd'hui**, calculée à partir des variations d'index MQTT, avec restauration d'état après redémarrage.
- **Historique REST** : prévisualisation, puis fusion contrôlée des historiques de soutirage et d'injection avec les statistiques natives du tableau de bord Énergie.
- **Bouton d'actualisation REST**, diagnostics des trames valides et des erreurs CRC.
- Interface traduite en **français et anglais**.
- Carte Lovelace complémentaire dans le [dépôt WiFiTIC Card](https://github.com/AuroreVgn/wifiTIC_card).

Les données du compteur sont lues à travers le module **[WiFiTIC de Cartelectronic](https://cartelectronic.fr/accueil/136-wifitic.html)** ; l'intégration ne nécessite pas de connexion à un compte Enedis ou EDF.

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

L'intégration associe **MQTT** (mesures en temps réel) et **REST** (informations du module, contrat, diagnostics et historiques).

```text
Compteur Linky ── téléinformation TIC ──► WiFiTIC
                                          │
                           ┌──────────────┴──────────────┐
                           │                             │
                          MQTT                          REST
                           │                             │
                   Broker MQTT                    API HTTP locale
                           │                             │
                           └───────────┬─────────────────┘
                                       ▼
                              Home Assistant
```

### 1. Configurer le broker MQTT dans Home Assistant

Home Assistant et le **[module WiFiTIC de Cartelectronic](https://cartelectronic.fr/accueil/136-wifitic.html)** doivent se connecter au **même broker MQTT**. Le broker reçoit les messages du module ; l'intégration MQTT officielle de Home Assistant permet ensuite à WiFiTIC de s'abonner à ces messages.

#### A. Installer Mosquitto broker (Home Assistant OS)

1. Dans Home Assistant, ouvrir **Paramètres → Modules complémentaires** (ou **Paramètres → Applications**, selon la version).
2. Ouvrir la boutique des modules complémentaires, rechercher **Mosquitto broker** et l'installer.
3. Dans la page du module, activer **Démarrer au démarrage** et, si souhaité, **Watchdog**.
4. Démarrer **Mosquitto broker**.
5. Ouvrir l'onglet **Journal** et vérifier l'absence d'erreur au démarrage.

> [!NOTE]
> Sur Home Assistant Container ou Core, le magasin de modules complémentaires n'est pas disponible. Il faut utiliser un broker Mosquitto externe, par exemple sur un autre hôte ou conteneur Docker, puis configurer l'intégration MQTT avec son adresse.

#### B. Créer un utilisateur MQTT

1. Aller dans **Paramètres → Personnes → Utilisateurs** (ou l'écran de gestion des utilisateurs de votre version).
2. Créer un utilisateur dédié, par exemple `mqtt_wifitic`, avec un **mot de passe fort**.
3. Utiliser ces identifiants dans la configuration MQTT du **module WiFiTIC**.
4. Vérifier que Mosquitto accepte bien les connexions de cet utilisateur.

Le broker Mosquitto fourni par Home Assistant peut utiliser les comptes Home Assistant pour l'authentification. Il est aussi possible de définir des comptes supplémentaires dans la configuration du module complémentaire, selon son mode d'authentification. **Ne pas publier le mot de passe dans une issue GitHub ou dans des captures d'écran.**

#### C. Configurer l'intégration MQTT officielle

1. Aller dans **Paramètres → Appareils et services → Ajouter une intégration**.
2. Rechercher **MQTT** et sélectionner l'intégration officielle.
3. Avec le module complémentaire Mosquitto, Home Assistant peut détecter automatiquement le broker ; accepter la découverte si elle correspond au bon broker.
4. Sinon, renseigner l'**hôte**, le **port** (généralement `1883` sans TLS), l'**identifiant** et le **mot de passe** du broker.
5. Vérifier que l'intégration MQTT apparaît **configurée et connectée**.

L'adresse du broker à saisir dans **WiFiTIC** est une adresse **joignable depuis le module physique** sur le réseau local. Ce n'est pas forcément l'adresse utilisée en interne par Home Assistant.

#### D. Vérifier l'accès réseau

- Le port TCP **1883** doit être accessible du module WiFiTIC vers le broker pour une connexion MQTT non chiffrée.
- Si un pare-feu ou un VLAN sépare les appareils, autoriser cette connexion.
- Ne **pas** exposer le port 1883 sur Internet.
- Le protocole et le port doivent correspondre : `mqtt://` pour une connexion classique, `mqtts://` uniquement si TLS est effectivement configuré.

**Aucun capteur MQTT YAML ni MQTT Discovery n'est nécessaire** : l'intégration WiFiTIC crée elle-même les entités.

### 2. Configurer MQTT sur le module WiFiTIC

Ouvrir l'interface Web du **[WiFiTIC de Cartelectronic](https://cartelectronic.fr/accueil/136-wifitic.html)**, puis **CONFIGURATION → MQTT**. Les champs ci-dessous correspondent à l'interface du module.

| Champ affiché dans WiFiTIC | Valeur / rôle |
| --- | --- |
| **Activation** | Activer MQTT |
| **Serveur MQTT** | URL du broker, sous la forme `mqtt://ADRESSE_IP_DU_BROKER` (et non une simple IP) |
| **Authentification** | Activer si le broker exige un utilisateur et un mot de passe |
| **Identifiant** | Compte MQTT dédié, par exemple `mqtt_wifitic` |
| **Mot de passe** | Mot de passe du compte MQTT |
| **QoS** | `QoS 0` dans la configuration illustrée ; laisser cette valeur pour commencer |
| **Topic Racine MQTT** | `wifitic` dans le champ |
| **Ajout du sous-élément racine '/'** | **Coché** dans la configuration illustrée |
| **ENREGISTRER** | Enregistrer les paramètres sur le module |
| **DISCOVERY** | Fonction distincte de l'intégration personnalisée WiFiTIC ; ne pas l'activer pour créer des entités en double |

Exemple **anonymisé**, reproduisant les réglages de l'interface :

```text
Activation                     : Activée
Serveur MQTT                   : mqtt://192.168.1.100
Authentification               : Activée
Identifiant                    : mqtt_wifitic
Mot de passe                   : ********
QoS                            : QoS 0
Topic Racine MQTT              : wifitic
Ajout du sous-élément racine / : Coché
```

L'adresse `192.168.1.100` est **fictive** : la remplacer par l'adresse locale réelle du broker Mosquitto. Les identifiants sont des exemples et ne correspondent pas à ceux de la capture.

> [!IMPORTANT]
> **Ne pas saisir `/wifitic` dans le champ « Topic Racine MQTT » si l'option « Ajout du sous-élément racine '/' » est cochée.** Avec le champ `wifitic` et cette case cochée, le module publie sous la racine `/wifitic`, attendue par défaut par l'intégration Home Assistant. Si vous décochez la case, vérifiez les sujets réellement publiés et adaptez le sujet racine dans l'intégration.

Après avoir cliqué sur **ENREGISTRER**, vérifier l'indicateur d'état de connexion MQTT en haut à droite du panneau. Un indicateur positif est utile, mais **la réception des messages dans Home Assistant reste la vérification déterminante**.

Si le module propose **DISCOVERY**, ce mécanisme est destiné à la découverte automatique MQTT. Il n'est **pas nécessaire** pour l'intégration personnalisée `wifiTIC`, qui gère ses propres entités. Éviter de déclencher une découverte supplémentaire si vous ne souhaitez pas de doublons.

### 3. Vérifier les publications MQTT

Dans **Paramètres → Appareils et services → MQTT → Configurer → Écouter un sujet**, écouter :

```text
/wifitic/#
```

Les deux sujets attendus par le code, pour un sujet racine `/wifitic`, sont :

| Sujet | Contenu |
| --- | --- |
| `/wifitic/teleinfo` | Message JSON contenant les mesures, index, tarifs et relais |
| `/wifitic/online` | Disponibilité du module (`true`, `1`, `online`, `on` pour l'état en ligne) |

Exemple **simplifié** de message sur `/wifitic/teleinfo` :

```json
{
  "consumption": {
    "phases": [{"app": 1189, "iinst": 5}],
    "runningPeriod": "Heures pleines jour normal",
    "counters": [{"value": 37327777}, {"value": 23593133}],
    "relay": {"r1": false, "r2": false}
  },
  "production": {"counter": 8979143, "pprod": 0},
  "counter": {"state": "ok", "contract": 11, "psous": 9, "pcoup": 9,
              "phases": [{"voltage": 230}]}
}
```

La structure exacte et le nombre d'index dépendent des informations envoyées par le compteur.

Si aucun message n'arrive, vérifier **l'adresse du broker**, les identifiants, la connexion réseau, la publication MQTT du module et surtout le **slash initial** du sujet.

### 4. Ajouter l'intégration WiFiTIC

Dans **Paramètres → Appareils et services → Ajouter une intégration → WiFiTIC**, renseigner :

| Champ | Description |
| --- | --- |
| Hôte | IP ou nom d'hôte du module WiFiTIC (API REST locale en HTTP) |
| Utilisateur | Identifiant REST si une authentification est configurée |
| Mot de passe | Mot de passe REST correspondant |
| Sujet MQTT racine | `/wifitic` par défaut ; doit correspondre exactement au topic configuré sur le module |

L'assistant teste l'API `/rest/teleinfo` et identifie le compteur pour éviter les doublons. Les identifiants REST ne sont **pas nécessairement** ceux du broker MQTT.

L'intégration attend l'arrivée des données MQTT et retente son abonnement si MQTT n'est pas encore disponible. Les données REST restent accessibles indépendamment.

### 5. Actualisation et historique

Les informations REST sont actualisées automatiquement **toutes les 5 minutes** ; les données MQTT sont reçues dès leur publication. Les compteurs de diagnostic CRC sont désactivés par défaut.

Pour l'importation des données historiques, consulter la rubrique **🕰️ Importation de l'historique énergétique** plus bas.

## 📊 Entités créées

### Consommation et injection

| Capteur | Source | Unité / particularité |
| --- | --- | --- |
| Puissance apparente soutirée | MQTT `consumption.phases[0].app` | VA |
| Puissance soutirée du réseau (estimée) | MQTT, calcul à partir de la puissance apparente | W ; facteur estimé **0,95** |
| Intensité instantanée | MQTT `consumption.phases[0].iinst` | A |
| Tension réseau | MQTT `counter.phases[0].voltage` | V |
| Puissance injectée sur le réseau | MQTT `production.pprod` | W |
| Index énergie injectée au réseau | MQTT `production.counter` | Wh, cumul croissant |
| Index énergie soutirée – *nom de période* | MQTT `consumption.counters[n].value` | Wh, un capteur par index |
| Énergie soutirée aujourd'hui | Variations des index MQTT | Wh, remise à zéro quotidienne |
| Énergie injectée aujourd'hui | Variations de l'index d'injection MQTT | Wh, remise à zéro quotidienne |

La puissance soutirée en watts est **une estimation** (`VA × 0,95`) et non une mesure directe de puissance active. Les deux capteurs d'énergie quotidienne restaurent leur état après redémarrage et gèrent le changement de jour.

Les index cumulés sont compatibles avec les statistiques longue durée de Home Assistant (`device_class: energy`, `state_class: total_increasing`). Ils sont utilisables dans le tableau de bord **Énergie**.

### Contrat et période courante

| Capteur | Rôle |
| --- | --- |
| Période tarifaire | Période active (`consumption.runningPeriod`) |
| Contrat électrique | Nom déterminé à partir des informations REST |
| État de la téléinformation | État du compteur |
| Puissance souscrite au contrat | Valeur `psous` en kVA |
| Seuil de coupure Linky | Valeur `pcoup` en kVA |
| Profil tarifaire fournisseur aujourd'hui | Code `currentDaySupplier` (champ TIC `NJOURF`) |
| Profil tarifaire fournisseur demain | Code `nextDaySupplier` (champ TIC `NJOURF+1`) |

Les noms des index proviennent de `/rest/teleinfo/periods`. Pour **EDF Zen Flex** (code contrat `11`), les libellés « pointe » sont présentés comme « sobriété ». Les périodes HC/HP disposent d'icônes adaptées.

Les profils fournisseur sont exposés sous leur **code brut** : ils ne constituent pas une prévision de prix du kWh.

### Diagnostics

| Entité | Type | Particularité |
| --- | --- | --- |
| Trames TIC valides | Capteur REST | Diagnostic, désactivé par défaut |
| Erreurs de transmission TIC (CRC) | Capteur REST | Diagnostic, désactivé par défaut |
| Relais 1 à 8 | Huit capteurs binaires MQTT | Diagnostic, désactivés par défaut |
| Actualiser les données REST | Bouton | Actualisation manuelle du coordinateur REST |

Les relais lisent `consumption.relay.r1` à `r8`. Leur état est informatif : le bouton d'actualisation ne commande pas les relais.

### Provenance des données

| API / sujet | Utilisation |
| --- | --- |
| `/wifitic/teleinfo` | Puissances, mesures, index, tarifs, relais |
| `/wifitic/online` | Disponibilité du module |
| `/rest/teleinfo` | Informations générales du compteur et contrat |
| `/rest/teleinfo/periods` | Libellés des périodes tarifaires |
| `/rest/teleinfo/jour` | Données journalières REST consultées par l'intégration |
| `/rest/debug/teleinfo` | Trames TIC valides et erreurs CRC |
| `/rest/configuration` et `/rest/configuration/MQTT` | Informations de configuration |
| `/rest/data/{year}/{day}` | Historique énergétique |

Les API REST sont locales au module **[WiFiTIC de Cartelectronic](https://cartelectronic.fr/accueil/136-wifitic.html)**.

## 🕰️ Importation de l'historique énergétique

L'intégration peut compléter les **statistiques natives MQTT** de Home Assistant avec les données historiques REST antérieures à la mise en service de l'intégration. Elle traite l'**injection** et le **soutirage**, y compris les index de consommation par période.

### 1. Sauvegarder Home Assistant

Avant toute modification, réaliser une **sauvegarde incluant Recorder**. La fusion modifie les statistiques longue durée et ne constitue pas une simple mise à jour d'entité.

### 2. Prévisualiser l'historique REST

Dans **Outils de développement → Actions**, sélectionner `wifitic.preview_history` et fournir une plage de dates :

```yaml
action: wifitic.preview_history
data:
  start_date: "2026-10-05"
  end_date: "2026-10-08"
```

Cette action n'écrit pas dans Recorder.

### 3. Simuler la fusion avec les statistiques natives

```yaml
action: wifitic.merge_native_energy_history
data:
  start_date: "2026-10-05"
  end_date: "2026-10-08"
  include_injection: true
  include_consumption: true
  confirm_write: false
```

- `include_injection` : traiter l'énergie exportée vers le réseau.
- `include_consumption` : traiter les index de soutirage.
- `confirm_write: false` : **prévisualisation uniquement**.
- `config_entry_id` : facultatif lorsqu'une seule intégration WiFiTIC est configurée.

### 4. Confirmer après contrôle

Vérifier les périodes, les valeurs et le raccordement avec la première heure MQTT native. Relancer ensuite la même action avec `confirm_write: true` **uniquement si le résultat est cohérent**.

> [!CAUTION]
> Les écritures Recorder ne sont **pas atomiques**. Après une erreur, certaines heures peuvent déjà avoir été importées. Ne pas relancer sans vérifier les statistiques existantes. Éviter tout chevauchement et tout double comptage.

### 5. Vérifier le tableau de bord Énergie

Dans **Paramètres → Tableaux de bord → Énergie**, sélectionner les index de consommation dans **Consommation du réseau** et l'index d'injection dans **Retour au réseau**.

> [!IMPORTANT]
> La valeur `production.counter` du module WiFiTIC correspond à **l'injection réseau** et **non à la production photovoltaïque totale**. Avec une batterie ou de l'autoconsommation, les deux mesures sont différentes.

L'historique REST peut comporter différents formats selon le micrologiciel du module ; les données sont rapprochées des heures de statistiques Home Assistant avant fusion.

## 🧩 Carte Lovelace

La carte est distribuée dans un dépôt distinct : **[WiFiTIC Card](https://github.com/AuroreVgn/wifiTIC_card)**.

Elle permet de présenter les informations WiFiTIC dans un tableau de bord Home Assistant. Consulter son dépôt pour connaître son état de publication.

## ℹ️ Fonctionnement et limites

- **MQTT** fournit les mesures en temps réel ; **REST** fournit notamment le contrat, les périodes, les diagnostics et l'historique.
- L'intégration interroge REST toutes les **300 secondes** et renouvelle une tentative d'abonnement MQTT toutes les **30 secondes** lorsque nécessaire.
- Le sujet MQTT racine doit correspondre exactement à celui du module, slash initial compris.
- Les index de consommation dépendent du contrat et des périodes réellement exposées.
- Les mesures instantanées et les index ne sont pas reconstruits à partir de REST si MQTT est indisponible.
- Les capteurs de diagnostic et relais sont désactivés par défaut.
- La puissance soutirée en W est une **estimation**, non une mesure certifiée.
- Les historiques disponibles dépendent des données conservées par le **[module WiFiTIC de Cartelectronic](https://cartelectronic.fr/accueil/136-wifitic.html)**.
- L'injection réseau n'est pas la production photovoltaïque totale.
- La migration historique nécessite une sauvegarde et un contrôle des statistiques existantes.

## 🤝 Signaler un problème

Ouvrir une [issue GitHub](https://github.com/AuroreVgn/wifiTIC/issues) en indiquant la version de Home Assistant, la version de l'intégration, le comportement attendu et les journaux utiles **sans données personnelles**.

## 📄 Licence

La licence sera précisée lors de la publication du fichier `LICENSE`.

---

**WiFiTIC** est un projet indépendant, développé pour la communauté Home Assistant.
