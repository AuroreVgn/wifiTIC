# 📊 WiFiTIC — Home Assistant

Intégration personnalisée Home Assistant pour un compteur **WiFiTIC**, combinant les données locales REST et MQTT du compteur Linky.

## ✨ Fonctionnalités

- Capteurs de consommation, d’injection réseau et index tarifaires via MQTT.
- Prise en charge des périodes tarifaires, notamment EDF Zen Flex.
- Consultation de l’historique REST.
- Raccordement de l’historique REST d’**injection** et de **soutirage** aux statistiques natives MQTT du tableau Énergie.

## 📦 Installation

Copier `custom_components/wifitic` dans le répertoire `config/custom_components/` de Home Assistant, puis redémarrer Home Assistant. Ajouter ensuite l’intégration WiFiTIC depuis **Paramètres → Appareils et services**.

Le broker MQTT et le compteur WiFiTIC doivent être configurés et accessibles.

## 📊 Importer l’historique énergétique

Prévisualisation sans écriture :

```yaml
action: wifitic.merge_native_energy_history
data:
  start_date: "2026-10-05"
  end_date: "2026-10-08"
  include_injection: true
  include_consumption: true
  confirm_write: false
```

Pour écrire, utiliser `confirm_write: true` **après avoir contrôlé le résultat de prévisualisation**.

> ⚠️ Les écritures de statistiques Recorder ne sont pas atomiques. Ne relancez pas aveuglément une importation après une erreur. Sauvegardez la base Home Assistant avant une migration. Les index d’injection WiFiTIC correspondent à l’**export réseau**, et non à la production solaire totale.

Le service `wifitic.preview_history` permet également d’inspecter les séries REST et MQTT sans écriture.

## 📝 Version

**0.0.1** — Première version publique, basée sur la version de préproduction 1.0.45, avec suppression des services d’importation redondants.

## ❤️ Soutenir

Projet communautaire maintenu par [AuroreVgn](https://github.com/AuroreVgn).
