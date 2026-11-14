# ClaudeUsage

Récupère toutes les heures les données d'utilisation de claude.ai et les stocke dans
une base SQLite locale (`data/usage.sqlite3`).

> ⚠️ L'endpoint `/api/organizations/<org>/usage` n'est pas une API officielle :
> il peut changer ou être bloqué sans préavis.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env   # puis remplir CLAUDE_ORG_ID et CLAUDE_COOKIES
```

## Utilisation

```powershell
.venv\Scripts\python -m claude_usage --once    # une collecte (test)
.venv\Scripts\python -m claude_usage           # boucle infinie (toutes les heures)
```

En production, [HomeRun](../homerun) lance `--once` toutes les heures (tâche
`claude_usage_collect`) et sert le tableau de bord (service `claude_usage_web`) : ne pas
lancer la boucle à la main en parallèle. Le mode boucle reste utile hors HomeRun.

Quand la session expire, le journal (`logs/collector.log`) affiche une erreur HTTP 401/403 :
recopiez alors le cookie depuis le navigateur dans `.env`.

## Cookies

Les cookies du `.env` servent de point de départ. Les cookies renvoyés par le serveur
sont fusionnés et enregistrés dans `data/cookies.json` (secret, ignoré par git), puis
réutilisés aux collectes suivantes. Modifier `CLAUDE_COOKIES` dans `.env` réinitialise
ce fichier. Le journal indique, pour chaque cookie reçu, son nom, son expiration et si
sa valeur a changé (jamais la valeur elle-même).

## Données

- `snapshots` : horodatage UTC + JSON brut de la réponse
- `usage_windows` : une ligne par fenêtre (`five_hour`, `seven_day`, …) avec
  `utilization` (%) et `resets_at`

## Tableau de bord web

Servi par HomeRun (waitress + WhiteNoise) sur `http://<IP Tailscale>:8060/`. Ajouter l'IP
Tailscale à `ALLOWED_HOSTS` dans `.env`.

En développement :

```powershell
.venv\Scripts\python manage.py runserver
```

Puis ouvrir http://127.0.0.1:8060/ (port par défaut) : courbes 5 h (bleu) et semaine (jaune), plus la courbe
du supplément (rouge) seulement si elle dépasse 0 sur la période. Échelle fixe de 0 à 100 %,
7 derniers jours par défaut (liens pour 24 h, 30 jours, tout).

Le bouton **Actualiser** lance un relevé immédiat. La collecte horaire n'est pas modifiée.

## Alertes Discord

Renseigner `DISCORD_WEBHOOK_URL` dans `.env` (Discord : paramètres du salon > Intégrations >
Webhooks > Nouveau webhook > Copier l'URL). Un message est envoyé quand la collecte commence
à échouer (cookies expirés, erreur réseau, configuration, base de données), puis un autre quand
elle fonctionne à nouveau. Une même erreur répétée n'est signalée qu'une fois.
