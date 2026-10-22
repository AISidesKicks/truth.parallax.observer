"""The demo scripts.

A demo is a conversation with the visitor's side written down. The agent
answers live, the way it would to a real visitor, and the reader watches the
machinery: which tactic it picked, which facts it reached for, how its mood
moved.

Each script exercises a different path through the agent:

    the opening question      something the corpus can answer
    the push back              a specific objection, so the tactic has to change
    the blind spot              something the corpus does not cover, so the
                                agent has to say it does not know
    the partial agreement      so the mood moves and the agent stops pushing
    the last word              so the script ends on something

The visitor can take over at any point. The script stops and the reader
becomes the visitor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DemoLine:
    """One thing the visitor says."""

    text: str
    note: str = ""
    pause: float = 1.2


@dataclass
class Demo:
    """A whole scripted conversation."""

    id: str
    title: str
    belief: str
    worldview: str
    blurb: str
    lines: list[DemoLine] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """The demo as the interface sees it."""
        return {
            "id": self.id,
            "title": self.title,
            "belief": self.belief,
            "worldview": self.worldview,
            "blurb": self.blurb,
            "lines": [
                {"text": line.text, "note": line.note, "pause": line.pause}
                for line in self.lines
            ],
        }


DEMOS: list[Demo] = [
    Demo(
        id="flat-earth-horizon",
        title="The horizon",
        belief="the Earth is flat",
        worldview="spherical-earth",
        blurb=(
            "The classic one. A question the corpus answers well, then a "
            "push back, then something the corpus has no answer for."
        ),
        lines=[
            DemoLine(
                "how do you explain the horizon then",
                "the corpus is full of geodesy here",
            ),
            DemoLine(
                "I have seen the curve on a lake with my own eyes though",
                "a specific objection, so the tactic has to change",
                pause=1.6,
            ),
            DemoLine(
                "what about the photos from space, those are real",
                "the images are in the corpus too",
                pause=1.6,
            ),
            DemoLine(
                "and what would it take to convince me the other way",
                "outside the corpus, the agent has to say so",
                pause=1.8,
            ),
            DemoLine(
                "ok that is a fair point",
                "the visitor concedes, the mood moves",
                pause=1.6,
            ),
        ],
    ),
    Demo(
        id="flat-earth-edinburgh",
        title="The Edinburgh experiment",
        belief="the Earth is flat",
        worldview="spherical-earth",
        blurb=(
            "A flat earther's best experiment, argued against with the "
            "measurement rather than with a slogan."
        ),
        lines=[
            DemoLine(
                "you keep talking about curvature, but has anyone ever "
                "actually measured it",
                "the history of the measurement is in the corpus",
            ),
            DemoLine(
                "the Edinburgh experiment gave the same answer as a table "
                "on a mountain, and you know it",
                "a specific historical counter",
                pause=1.8,
            ),
            DemoLine(
                "so what was wrong with it then",
                "the answer is in the corpus, and it is not a dodge",
                pause=1.8,
            ),
            DemoLine(
                "that does not sound like a conspiracy to me",
                "the visitor half believes it",
                pause=1.6,
            ),
            DemoLine(
                "ok that is a fair point, I had not thought of it that way",
                "the visitor concedes, the mood moves",
                pause=1.6,
            ),
        ],
    ),
    Demo(
        id="discworld-edge",
        title="The Edge",
        belief="the Earth is a disc",
        worldview="spherical-earth",
        blurb=(
            "A visitor who is quite happy in a disc world, and is not "
            "going to be moved by an appeal to a globe."
        ),
        lines=[
            DemoLine(
                "my world is a disc, carried by elephants on a turtle, and "
                "that is fine",
                "the corpus is the discworld one here",
            ),
            DemoLine(
                "but you are arguing the Earth is round, and everyone knows "
                "that is the official story",
                "the official story is a tactic of its own",
                pause=1.8,
            ),
            DemoLine(
                "what is at the Edge then, in your version",
                "the corpus knows, and the answer is not funny",
                pause=1.8,
            ),
            DemoLine(
                "that is just a story you tell children",
                "the visitor pushes back hard",
                pause=1.6,
            ),
            DemoLine(
                "ok that is a fair point, about the experiments anyway",
                "a partial concession, the mood moves",
                pause=1.6,
            ),
        ],
    ),
    Demo(
        id="norse-nine-worlds",
        title="The nine worlds",
        belief="the Earth has nine worlds",
        worldview="spherical-earth",
        blurb=(
            "The thinnest corpus in the lab, and the one where the model "
            "has the least to hold on to."
        ),
        lines=[
            DemoLine(
                "there are nine worlds, and Midgard is the one you live on",
                "the Poetic Edda is the corpus here",
            ),
            DemoLine(
                "and you are going to tell me a sphere is better than that",
                "the corpus has almost nothing on a sphere",
                pause=1.8,
            ),
            DemoLine(
                "how do you even know what a sphere is, you have only ever "
                "seen one",
                "outside the corpus again",
                pause=1.8,
            ),
            DemoLine(
                "fine, tell me about the tree then",
                "the corpus is strong here",
                pause=1.6,
            ),
            DemoLine(
                "ok that is a fair point, about the tree",
                "the visitor concedes, the mood moves",
                pause=1.6,
            ),
        ],
    ),
]


def get_demo(demo_id: str) -> Demo | None:
    """One demo, by id."""
    for demo in DEMOS:
        if demo.id == demo_id:
            return demo
    return None


def demo_list() -> list[dict[str, Any]]:
    """Every demo, for the interface."""
    return [demo.to_dict() for demo in DEMOS]
