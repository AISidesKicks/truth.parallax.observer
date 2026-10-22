# Embeddings: the encoder, the image tier, and the dialects

> How the corpus gets its vectors, and what breaks when the sizes are wrong.

## The encoder

There is one encoder and it is EmbeddingGemma 2, served by the same llama.cpp
router as the chat model. The separate embedding server is gone.

| Property | Value |
|---|---|
| Model | `embeddinggemma-2` |
| File | `embeddinggemma-2-Q8_0.gguf` |
| Quant | Q8_0 |
| Size | 310 MB |
| Dimensions | 768, Matryoshka down to 128 |
| Context | 4096 tokens, see below |
| Pooling | mean, not last |
| Vision | the projector is wired, `mmproj-embeddinggemma-2-Q8_0.gguf` |

The model is multimodal: 270M of text encoder, 170M of vision and 300M of
audio. The text part is what the corpus uses today.

The `gemma-embedding2` architecture needs a llama.cpp build from 11455 on.
The image tag `server-cuda13` carries it, but the tag moves, so an old cached
pull answers `unknown model architecture` and it looks like a broken model
file. The `server-cuda-b4738` line has the router removed and cannot serve
the two models from one port at all.

## The preset

The encoder runs as a preset in `config/llama-models.ini`, next to the chat
model. The section name is the model id.

```ini
[embeddinggemma-2]
model = /models/embeddinggemma-2-Q8_0.gguf
mmproj = /models/mmproj-embeddinggemma-2-Q8_0.gguf
embeddings = true
pooling = mean
ctx-size = 4096
batch-size = 4096
ubatch-size = 4096
load-on-startup = false
```

The `embeddings = true` line is what turns the instance into an encoder
instead of a generator, and it has to be set per preset.

### The context and the batch size

The batch size has to match the context, and the context has to be 4096.

At 2048 the symbol dense chunks, the geodesy formulas, were rejected with
`input is too large to process`. The batch was smaller than the longest
chunk, so the encoder refused it. At 4096 with `batch-size` and
`ubatch-size` both at 4096, the formulas go in.

This is not a tuning knob, it is a floor. If a chunk ever gets longer than
4096 tokens, the context has to grow with it, and the batch with it.

`load-on-startup = false` keeps the encoder off the card until something asks
for a vector. The chat model is the one that is always loaded.

## Who embeds what

The app never embeds anything. OpenViking does.

```
the app            ->  find(query, target_uri)      ->  OpenViking
OpenViking         ->  the encoder                   ->  llama.cpp router
the app            ->  the chat model                ->  llama.cpp router
```

That is why `VIKING_EMBEDDING_BASE` points at the router in the compose file,
and why the memory server needs the api key for it.

## The two dialects

The router speaks the OpenAI dialect, `/v1/embeddings` with
`{"model": ..., "input": ...}`, and so does OpenViking when it calls the
encoder. That part lines up.

The part that does not line up is the two ways of saying the same thing, and
they have to be kept apart:

| The app | The memory server |
|---|---|
| `LLM_API_BASE`, the chat model | `VIKING_EMBEDDING_BASE`, the encoder |
| `EMBEDDING_MODEL`, the name only | `VIKING_EMBEDDING_MODEL`, the name only |
| the app picks the model id | the server picks the model id |

The model name is the same in both, the base url is not, and the app and the
memory server live in different containers, so the url that works for one
does not work for the other. The compose file sets the container names, and
`.env` holds the host side ones.

The other thing that bit us: the corpus lives in the **user** namespace, so
the client addresses it with the home alias, `viking://~/resources/knowledge`.
The account scope, `viking://resources/knowledge`, is empty and a retrieval
against it returns nothing at all. `pixi run verify` checks that on every
run, because a silent zero-hit retrieval is the failure mode that looks
exactly like a working stack.

## The image tier

The images are embedded, and the vectors live outside the corpus:

```
facts/images/<worldview>/<name>.embedding.json
```

Not inside it. Inside the corpus, OpenViking tries to embed seventeen
kilobytes of JSON and gives up. The vector files are the sidecar, and the
pictures themselves sit in the knowledge tier, under
`facts/knowledge/<worldview>/images/<name>/`.

The encoder has the projector, so the model can see. What is missing is the
other half: a query with a picture in it, and a model that reads the picture
that comes back. That is a goal in `plans/open-goals.md`, the vision tier.

## The reindex and the stale content

`reindex` re-embeds the fields the records already hold. It does not read the
files on disk again.

So when the corpus changes, the index keeps the old text until the tier is
dropped from the server first:

```bash
python scripts/migrate_to_viking.py --drop   # drop the tier
python scripts/migrate_to_viking.py --reindex # and put it back
```

Without the drop, a reindex re-embeds the old content and the change does not
appear. This is the same in the other direction, the tier has to exist in the
server for a reindex to have anything to work on.

## The checks

```bash
# a vector, and how big it is
curl -s http://localhost:11433/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "embeddinggemma-2", "input": "probe string"}' | jq '.data[0].embedding | length'

# the whole stack
pixi run verify
```

`pixi run verify` is the check that matters. It asks the encoder for a
vector and holds it to 768 dimensions, it asks the memory server for the
corpus, it does a scoped retrieval, and it does a retrieval in a worldview
that does not exist and expects nothing back.

The old `investigations/embeddings/infinity_test.py` is gone with that
server. The verify step replaced it.

## The files

| File | What it is |
|---|---|
| `config/llama-models.ini` | the encoder preset |
| `config/models.toml` | the catalogue entry for the encoder |
| `config/openviking.conf` | how the memory server reaches the encoder |
| `scripts/embed_images.py` | the image sidecars |
| `scripts/migrate_to_viking.py` | the seeding, the reindex and the drop |
| `scripts/verify_stack.py` | the checks |
