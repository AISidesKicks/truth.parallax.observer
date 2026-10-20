# Labs

Each lab is one experiment. The instructions say what to set up, what to do,
and what to write down. You do not need to code anything.

The lab pages live in [`docs/lab/`](../docs/lab/), which is what the site at
[truth.parallax.observer](https://truth.parallax.observer) publishes.

## The labs

| Lab | What it is |
|-----|------------|
| [01 - Three truths](docs/lab/01-three-truths.md) | The core experiment. One question, three bodies of knowledge. |
| [02 - Outside the training data](docs/lab/02-outside-training.md) | Where the model stops being able to check itself, and what it does instead. |
| [Lab index](docs/lab/README.md) | How the labs are organised |

## Before you start

```bash
pixi install
docker/fetch-models.sh
docker/up.sh
docker/status.sh
```

You want all four services up. The app is at `http://localhost:8668`, the
memory server at `http://localhost:1933`, Phoenix at `http://localhost:6006`.

## The corpus

Four worldviews, each one a separate tree under `viking://resources/`:

```
viking://resources/
├── knowledge/spherical-earth/scientific/
├── knowledge/flat-earth/{victorian,biblical,vedic}/
├── knowledge/discworld/fictional/
└── knowledge/norse/fictional/
```

Plus the ammunition tier:

```
viking://resources/enrichment/<worldview>/{catchphrases,misleading-facts,quotes}/
```

The UI shows which of these the agent reached for. That is the whole point of
the lab, so keep an eye on it.

## Writing up

A good lab write-up is a few hundred words plus the log. What you are looking
for is the moment the model stopped being a source and started being a
storyteller.
