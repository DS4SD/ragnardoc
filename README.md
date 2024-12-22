# RAGNARDoc

RAGNARDoc (RAG Native Automatic Reingest Docs) is a tool that runs natively on a developer workstation and automatically ingests local documents into various Retrieval Augmented Generation indexes. It is designed as a companion app for workstation RAG applications which would benefit from maintaining an up-to-date view of documents hosted natively on a user's workstation.

![ragnardoc duck](./ragnardoc.png)

## Configuration

The configuration for RAGNARDoc is managed by a yaml file. The default location is `$HOME/.ragnardoc/config.yaml`, but can be overloaded with the `RAGNARDOC_HOME` environment variable. All default values can be found in [config.yaml](./ragnardoc/config/config.yaml) in the codebase.

## Ingestion Plugins

RAGNARDoc operates with a plugin model for connecting to applications to ingest docs. Each plugin is responsible for connecting to a given app. RAGNARDoc's native ingestion capabilities are:

### AnythingLLM Desktop

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
            base_url: http://localhost:3001
            apikey: <YOUR API KEY>
    ```

## Future Ideas

* Auto-configure by inspecting common tools
* Per-ingestor inclusion / exclusion
* Abstract scrapers to allow non-local scraping