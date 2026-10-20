# Labs

Each lab is one experiment. The instructions say what to set up, what to do,
and what to write down. You do not need to code anything.

## The rules

1. Write down every claim the agent makes that you cannot verify yourself.
2. Write down every fact it cites, with the source. The UI shows the URIs it
   pulled, so you can check whether it cited what it actually read.
3. Keep the raw chat log. The interesting part is what it said when it was
   wrong, not the polished version afterwards.

## The labs

| Lab | What it is |
|-----|------------|
| [01 - Three truths](01-three-truths.md) | The core experiment. One question, three bodies of knowledge. |
| [02 - Outside the training data](02-outside-training.md) | Where the model stops being able to check itself, and what it does instead. |

## Before you start

```bash
pixi install
docker/fetch-models.sh
docker/up.sh
docker/status.sh
```

You want all five services up. The app is at `http://localhost:8668`, the
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
