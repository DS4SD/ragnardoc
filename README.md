# RAGNARDoc

RAGNARDoc (RAG Native Automatic Reingestion for Documents) is a tool that runs natively on a developer workstation and automatically ingests local documents into various Retrieval Augmented Generation indexes. It is designed as a companion app for workstation RAG applications which would benefit from maintaining an up-to-date view of documents hosted natively on a user's workstation.

![ragnardoc duck](https://github.com/DS4SD/ragnardoc/blob/main/ragnardoc.png)

## Quick Start

```sh
pip install ragnardoc
# Initialize ragnardoc on your system
ragnardoc init
# Add a directory to be ingested
ragnardoc add ~/Documents
# Run an ingestion
ragnardoc run
# Start as a background service
ragnardoc start & disown
```

## Configuration

The configuration for RAGNARDoc is managed by a yaml file. The default location is `$HOME/.ragnardoc/config.yaml`, but can be overloaded with the `RAGNARDOC_HOME` environment variable. All default values can be found in [config.yaml](https://github.com/DS4SD/ragnardoc/blob/main/ragnardoc/config/config.yaml) in the codebase.

### Configuring

To initialize your RAGNARDoc config, do the following:

```sh
mkdir -p ~/.ragnardoc
echo "scraping:
  roots:
    # Fill in with the list of directories to ingest
    - ~/Desktop
    - ~/Documents
" > ~/.ragnardoc/config.yaml
```

Once done, you can add entries to your `config.yaml` to add supported ingestion plugins (see below).

### Ingestion Plugins

RAGNARDoc operates with a plugin model for connecting to applications to ingest docs. Each plugin is responsible for connecting to a given app. RAGNARDoc's native ingestion capabilities are:

#### AnythingLLM Desktop

To configure a connection to [AnythingLLM](https://anythingllm.com/), follow these steps:

1. Download and install the desktop app from their site: https://anythingllm.com/desktop
2. In the app, go to settings (wrench icon in the bottom panel of the left-hand sidebar)
3. Under `Admin -> General Settings`, toggle on `Enable network discovery` and wait for the app to reload
4. Under `Tools`, select `Developer API`
5. Create a new API Key
6. Add the plugin to your config (default location `$HOME/.ragnardoc/config.yaml`)

```yaml
ingestion:
  plugins:
    - type: anything-llm
      config:
        apikey: <YOUR API KEY>
```

#### Open WebUI

To configure a connection to [Open WebUI](https://docs.openwebui.com/getting-started/), follow these steps:

1. Follow the [Getting Started](https://docs.openwebui.com/getting-started/) guide to get Open WebUI running locally. TLDR:

```sh
pip install open_webui
# Run without login
WEBUI_AUTH=False open-webui serve
```

2. Open the UI in a browser tab (http://localhost:8080 by default)
3. Click on the user icon (top right) and select `Settings`
4. Click `Account` on the left panel of the settings view
5. Click `Show` (right side) for `API keys`
6. Click `+ Create new secret key` under `API Key` to create a new API Key
7. Click the copy icon to copy the api key
8. Add the plugin to your config (default location `$HOME/.ragnardoc/config.yaml`)

```yaml
ingestion:
  plugins:
    - type: open-webui
      config:
        apikey: <YOUR API KEY>
```

## TODO

- Per-ingestor inclusion / exclusion
- Abstract scrapers to allow non-local scraping
