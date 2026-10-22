# HuggingFace: the model files and the token

> Where the GGUF files come from, and when a token is needed.

## The files

The models are GGUF files, they live on the host in `.models/llama/`, and
the container mounts that folder read only. So they have to be there before
the container starts.

```bash
docker/fetch-models.sh
```

| File | Repository | Size | What it is |
|---|---|---|---|
| `granite-4.0-h-tiny-Q4_K_M.gguf` | `ibm-granite/granite-4.0-h-tiny-GGUF` | 4231 MB | the chat model |
| `embeddinggemma-2-Q8_0.gguf` | `ggml-org/embeddinggemma-2-GGUF` | 310 MB | the encoder |
| `mmproj-embeddinggemma-2-Q8_0.gguf` | `ggml-org/embeddinggemma-2-GGUF` | 555 MB | the vision projector |

The projector is not optional. EmbeddingGemma 2 is multimodal and the
projector is the vision half of it. Without the file next to the model, the
encoder only reads text and the image tier does not work. The preset in
`config/llama-models.ini` points at it with the `mmproj` line.

The script skips what is already there and resumes a partial download, so it
is safe to run twice.

```bash
docker/fetch-models.sh --llm      # only the chat model
docker/fetch-models.sh --embed    # only the encoder and the projector
```

## The build the encoder needs

EmbeddingGemma 2 uses the `gemma-embedding2` architecture, and llama.cpp only
learned it in build 11455. The image tag `server-cuda13` carries it, and the
build it resolves to moves. On a fresh pull it is 11783, which is fine.

The failure looks like a broken model file:

```
unknown model architecture
```

That is an old build, not a bad download. Pull the image again:

```bash
docker compose --env-file ../.env -f docker/docker-compose.yml pull prlx-llm
```

The `server-cuda-b4738` line has the router removed, so it cannot serve the
chat model and the encoder from one port at all.

## The token

| What | Needs a token |
|---|---|
| granite-4.0-h-tiny | no |
| embeddinggemma-2 | no |
| the vision projector | no |

The models we run are open. The token is only for the things that are not.

| Reason | What it is |
|---|---|
| gated models | the license has to be accepted on the model page first |
| rate limits | anonymous downloads are slow |
| private models | your own repos |

### Getting one

1. An account at <https://huggingface.co/join>, and verify the email.
2. For a gated model, open the model page, click "Access repository", read
   the terms, and wait for the approval.
3. A token at <https://huggingface.co/settings/tokens>. Read is enough.
4. Copy it, it is only shown once.

### Keeping it

In the environment:

```bash
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

Or in `.env`, which is gitignored:

```
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

The compose file passes it through:

```yaml
environment:
  - HF_TOKEN=${HF_TOKEN:-}
```

The file is in `.gitignore`, along with `.env.local` and `*.env`. A token in
the repository is a token in the world.

## The rules

| Do | Do not |
|---|---|
| keep it in the environment | commit it |
| use a read token | use a write token when read is enough |
| use a fine grained token | hand out a full access token |
| rotate it now and then | put it in a code file |
| keep it out of chat | paste it into a log |

## The troubleshooting

**401.** The token is missing or wrong. Check that it is set, and log in with
the CLI to be sure:

```bash
pip install huggingface-hub
huggingface-cli login --token hf_xxx
```

**The access to the model is restricted.** The license was not accepted.
Open the model page, accept the terms, and wait for the approval.

**Rate limits.** Set the token, an authenticated request gets the priority
bandwidth.

**The download is slow.** The file is 4.2 GB. The `curl` in the fetch script
resumes, so a slow link does not mean starting over.

## The files

| File | What it is |
|---|---|
| `docker/fetch-models.sh` | the downloads |
| `.models/llama/` | the files, they are not in git |
| `config/llama-models.ini` | the presets that point at them |
| `config/models.toml` | the catalogue entry for each file |
| `.env.sample` | the token, empty |
