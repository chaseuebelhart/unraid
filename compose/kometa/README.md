# Kometa Configuration

Kometa (formerly Plex Meta Manager) requires a YAML configuration file to operate.

## Directory Structure

```
kometa/
├── README.md          # This file
└── config/            # Create this directory
    ├── config.yml     # Main configuration file
    └── assets/        # Poster and metadata assets (optional)
```

## Setup Instructions

1. **Create the config directory** (if it doesn't exist):
   ```bash
   mkdir -p appdata/kometa
   ```

2. **Create the main config file** at `appdata/kometa/config.yml`:
   ```yaml
   ## Kometa Configuration File
   
   libraries:
     Movies:
       collection_files:
         - pmm: basic
         - pmm: imdb
       overlay_files:
         - pmm: resolution
         - pmm: audio_codec
     TV Shows:
       collection_files:
         - pmm: basic
         - pmm: imdb
       overlay_files:
         - pmm: resolution
         - pmm: audio_codec
   
   settings:
     cache: true
     cache_expiration: 60
     run_order:
       - operations
       - metadata
       - collections
       - overlays
   
   plex:
     url: http://plex:32400
     token: YOUR_PLEX_TOKEN
   
   tmdb:
     apikey: YOUR_TMDB_API_KEY
     language: en
   
   # Optional integrations
   # radarr:
   #   url: http://radarr:7878
   #   token: YOUR_RADARR_API_KEY
   #   root_folder_path: /data/media/movies
   #   quality_profile: HD-1080p
   #
   # sonarr:
   #   url: http://sonarr:8989
   #   token: YOUR_SONARR_API_KEY
   #   root_folder_path: /data/media/tv
   #   quality_profile: HD-1080p
   ```

3. **Get your Plex Token**:
   - Navigate to any media item in Plex Web
   - Click "Get Info" > "View XML"
   - Look for `X-Plex-Token=` in the URL

4. **Get TMDb API Key**:
   - Create account at https://www.themoviedb.org/
   - Go to Settings > API > Create API Key

## Environment Variables

The container expects these paths:
- `KOMETA_CONFIG=/config/config.yml`

## Running Kometa

Kometa runs on a schedule by default. To run manually:
```bash
docker exec -it kometa python kometa.py --run
```

## Documentation

Full documentation: https://kometa.wiki/
