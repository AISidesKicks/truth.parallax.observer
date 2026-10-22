# Development: the environments and the tasks

> pixi, three environments, and what to do when the GPU is not reachable.

## The environments

pixi manages the project. The environment is `prlx`, and there are three
setups on top of the shared core.

| Environment | What is in it | When |
|---|---|---|
| `default` | the core, the app and the scripts | day to day |
| `experiment` | the core plus pytest | running the tests |
| `benchmarks` | the core plus pandas, matplotlib, seaborn | the corpus and model benchmarks |
| `native` | the core plus llama.cpp from conda-forge | when the docker runtime cannot reach the GPU |

```bash
pixi info | grep Name        # the environment is prlx
pixi shell                  # into the shell
pixi run <task>             # a task, in the environment it wants
pixi run -e experiment <task>  # a task, in a named environment
```

Before installing anything, check that the environment is the right one:

```bash
pixi info | grep Name
```

The core dependencies are the app itself: fastapi, uvicorn, pydantic,
pydantic-settings, httpx, pyyaml, openai, python-dotenv, rich, psutil and
ruff, plus the OpenViking SDK and nvidia-ml-py from pypi. The
`pydantic-ai-slim` package with the openai extra is the typed client the
orchestrator uses.

## The tasks

```bash
# the stack
pixi run up            # docker/up.sh
pixi run down
pixi run status
pixi run logs
pixi run models        # the GGUF downloads

# the quality gate
pixi run test          # pytest, in the experiment environment
pixi run lint
pixi run format
pixi run verify        # the stack, end to end

# the corpus
pixi run fetch-wiki
pixi run chunk-knowledge
pixi run summarize-knowledge
pixi run expand-enrichment
pixi run prune-enrichment

# the memory server
pixi run viking-migrate
pixi run viking-reindex
pixi run viking-probe
pixi run corpus-stats
pixi run clean-sessions
```

`pixi run test` targets the experiment environment on its own, because pytest
is only in that one. `pixi run --environment experiment pytest -q` is the
same thing written out.

`pytest.ini` puts the project root on the path, so `import src.something`
works from the tests without setting anything up.

`pixi run format` rewrites the whole tree, including the python blocks
inside the markdown in `plans/`. It is a formatter, not a cleanup, so run it
on purpose and look at the diff.

## The tests

```bash
pixi run test
```

They do not need a GPU, a model server or a memory server. The two clients
are fakes in `tests/conftest.py`, they behave the way the real ones are
supposed to, and the app comes up without anything else running.

The scenarios in `plans/bdd-app.md` are the contract for the app. The tests
in `tests/` are how they are kept.

## Running the app on the host

The container is the normal way. The host path is for the scripts and for
looking at things closely.

```bash
# the app, on the host, against the containers
pixi run uvicorn src.main:app --port 8668
```

The host side of `.env` holds the host paths and the host urls. The container
side is in the compose file, and the compose `environment:` block wins over
`env_file:` for the same variable.

## The native fallback

The docker runtime needs the NVIDIA container toolkit, and the host kernel
module and the userspace libraries have to match. When they do not, the
container cannot open the card and the model server comes up empty.

It happened once. The host had kernel module 615.71.09 and libraries
615.71.10, and a reboot fixed it.

Until then, the `native` environment runs llama.cpp on the host, no container
involved:

```bash
pixi run -e native llama-server \
  --models-preset config/llama-models.ini \
  --host 0.0.0.0 --port 8080
```

The presets are the same file, so the model ids are the same and the app
does not care which one answered.

## The IDE

VS Code: `Ctrl+Shift+P` and "Python: Select Interpreter", then pick the pixi
environment. The interpreter is the one inside `.pixi/envs/`.

## The troubleshooting

### The environment is the wrong one

```bash
pixi info | grep Name      # it has to say prlx
```

### The model server does not answer

```bash
docker logs prlx-llm | tail -40
curl -s http://localhost:11433/v1/models
```

Two things come up here. The image tag, `server-cuda13`, moves, and an old
cached pull does not know the `gemma-embedding2` architecture and answers
`unknown model architecture`. And the `server-cuda-b4738` line has the
router removed.

### The corpus comes back empty

Two different failures look the same.

The account scope is empty, so a retrieval against
`viking://resources/knowledge` returns nothing. The corpus lives in the user
namespace, so the client has to use the home alias,
`viking://~/resources/knowledge`.

The wrong key looks the same too. The root key can reindex and cannot read
the tenant data. If the app container got the root key, every corpus read
comes back 403. The compose scripts pass `--env-file ../.env` for exactly
this reason.

`pixi run verify` tells the three apart.

### The interface did not change

The static files are served with `Cache-Control: no-store`, and that is on
purpose. Without it Chrome serves a stale `app.js` and an interface change
appears not to work.

### The GPU is not reachable from the container

```bash
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

If that fails, it is the toolkit or the kernel and library mismatch. The
native environment is the way to keep working.

## The files

| File | What it is |
|---|---|
| `pixi.toml` | the environments, the features and the tasks |
| `pytest.ini` | the test configuration |
| `ruff.toml` | the lint configuration |
| `.env` | the host side settings |
| `.env.sample` | the same, without the secrets |
