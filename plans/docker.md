# Docker: the prlx- stack

> Four services, one network, everything with a prefix.

## The stack

```
┌──────────────────────────────────────────────────────────────────────┐
│                            prlx-lab                                  │
│                                                                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐          │
│  │    prlx-llm    │  │  prlx-viking   │  │  prlx-phoenix  │          │
│  │                │  │                │  │                │          │
│  │ 11433 -> 8080  │  │ 1933           │  │ 6006, 4317/18  │          │
│  │ llama.cpp      │  │ OpenViking     │  │ Phoenix        │          │
│  │ router mode    │  │ 0.5.1.1        │  │ the traces     │          │
│  │                │  │                │  │                │          │
│  │ granite-4.0-   │  │ the corpus     │  └────────────────┘          │
│  │ h-tiny         │  │ the vectors    │                              │
│  │ embeddinggemma-│  │                │                              │
│  │ 2              │  └───────┬────────┘                              │
│  └───────┬────────┘          │                                       │
│          │                   │                                       │
│          └─────────┬─────────┘                                       │
│                    │                                                 │
│          ┌─────────▼─────────┐                                       │
│          │     prlx-app      │                                       │
│          │                   │                                       │
│          │ 8668              │                                       │
│          │ FastAPI, the      │                                       │
│          │ interface, the    │                                       │
│          │ agents            │                                       │
│          └───────────────────┘                                       │
└──────────────────────────────────────────────────────────────────────┘
```

There is a fifth service, `prlx-embed`. It is a standalone embedding server
and it is optional, it only exists for the case where the encoder wants a
CUDA context of its own. The default stack does not start it.

## The services

| Container | Image | Profile | Port | GPU | What |
|---|---|---|---|---|---|
| `prlx-llm` | `ghcr.io/ggml-org/llama.cpp:server-cuda13` | llm | 11433 | yes | the router, the chat model and the encoder |
| `prlx-embed` | `ghcr.io/ggml-org/llama.cpp:server-cuda13` | embed | 7997 | yes | the encoder on its own, optional |
| `prlx-viking` | the OpenViking image | viking | 1933 | no | the memory server, the corpus, the vectors |
| `prlx-phoenix` | `arizephoenix/phoenix:latest` | phoenix | 6006, 4317, 4318 | no | the traces, with the token counts |
| `prlx-app` | built from `docker/Dockerfile.app` | app | 8668 | no | the interface |
| `prlx-dev` | built from `docker/Dockerfile.app` | dev | 8668 | yes | the same, with hot reload and debug logging |

Everything carries the `prlx-` prefix: the containers, the network, the
volume. This Docker host is shared with other projects, and an unprefixed
container name is a collision waiting for a bad afternoon.

## Running it

```bash
cd docker

./fetch-models.sh   # the GGUF files, they live on the host
./up.sh             # llm + viking + phoenix + app
./up.sh dev         # llm + viking + phoenix + dev
./up.sh llm viking  # a chosen combination
./status.sh
./tests.sh
./down.sh
```

The app is at **http://localhost:8668**, the model server at
**http://localhost:11433/v1**, the memory server at
**http://localhost:1933**, and the traces at **http://localhost:6006**.

## The env file, and where it is read from

This is the part that bites.

The scripts run compose from inside `docker/`, so compose reads its
interpolation variables from `docker/.env`, which does not exist. The
scripts pass `--env-file ../.env` explicitly, and that flag is what makes
the interpolation work. It has to stay.

There are two different things going on, and they are easy to mix up:

| | What it does | Where it comes from |
|---|---|---|
| `env_file: ../.env` | the variables the container sees | the root `.env` |
| `--env-file ../.env` | the variables compose interpolates `${...}` with | the root `.env` |

So the compose file can write `${LLM_MODEL_ALIAS:-granite-4.0-h-tiny}` and it
resolves against the root `.env`, and the container also receives the root
`.env` as its environment.

`environment:` beats `env_file:` for the same variable, so the container side
values win where both are set. That is how `OPENVIKING_WORKSPACE` becomes
`/app/viking_data` inside the container while the root `.env` holds the host
path `memory/openviking`.

**Do not drop the `--env-file ../.env` flag.** Without it the app container
gets the root API key instead of the user key, and every corpus read comes
back 403. The stack looks fine, the model answers, and the retrieval is
empty.

## The two OpenViking keys

There are two keys and they are not interchangeable.

| Key | What it can do |
|---|---|
| the root key | reindex, administer |
| the user key | read the tenant data, which is where the corpus lives |

The corpus is in the **user** namespace. The root key can reindex it and
cannot read it.

## The volumes

| Host | Container | What |
|---|---|---|
| `.models/llama` | `/models` | the GGUF files, read only |
| `config/llama-models.ini` | `/app/models.ini` | the router presets, read only |
| `memory/openviking` | `/app/viking_data` | the memory workspace |
| `facts` | `/app/facts` | the corpus, read only in the app |
| `config` | `/app/config` | the catalogue and the viking config, read only |
| `.logs/app` | `/app/logs` | the app logs |
| `prlx-phoenix-data` | `/root/.phoenix` | the traces |

The memory workspace is big. The corpus is 79 MB, the vectors are 90 MB, and
the server internals are another 18 MB.

## The GPU

Three containers ask for the card: `prlx-llm`, `prlx-embed` and `prlx-dev`.
`prlx-app` does not need it, it only reads the metrics, and `nvidia-ml-py`
reads the driver directly without a CUDA context, so the monitoring bar gets
the GPU numbers without taking any of the card's memory.

The `prlx-embed` service is the one to think about. It is another CUDA
context on a card that already holds the chat model, and the chat model is
the one that has to stay responsive.

### When the driver breaks

It happened once: the host had kernel module 615.71.09 and the userspace
libraries were 615.71.10, and the container could not open the card. A
reboot fixed it, because the kernel and the libraries have to match.

The fallback is the native path, `pixi run -e native`, which runs llama.cpp
on the host without the container. See `plans/dev.md`.

## The checks

```bash
docker/tests.sh
```

It asks the model server what it serves, asks the memory server for its
health, and then runs `scripts/verify_stack.py`, which is the real check.
The eight checks are in `plans/open-goals.md` and in the script.

## The files

| File | What it is |
|---|---|
| `docker/docker-compose.yml` | the stack |
| `docker/Dockerfile.app` | the app image |
| `docker/Dockerfile.viking` | the memory server image |
| `docker/fetch-models.sh` | the GGUF downloads |
| `docker/up.sh` | start |
| `docker/down.sh` | stop |
| `docker/status.sh` | what is up |
| `docker/tests.sh` | the checks |
| `config/llama-models.ini` | the router presets |
| `config/models.toml` | the catalogue |
| `config/openviking.conf` | the memory server config, `${VAR}` and the server expands it |
