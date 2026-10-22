# BDD: the application

Status: slices 1 and 3 are implemented, slice 2 is partly. The app is
written from these scenarios. They came first, and they are the thing to read
if you want to know what the app is supposed to do.

The slices are in build order. Slice 1 is the vertical one, a working
PersuChat, and the rest hang off it.

| Slice | State |
|-------|-------|
| 1, PersuChat | done |
| 2, the lab view | done, the facts open, the pictures show, the arguments are counted |
| 3, Fire Chat | done |
| 4, the running system | half, the model and the corpus are reported, Phoenix is not wired |

## Slice 5: the watch mode

Not in the original plan, and it is the one that makes the lab a lab.

A demo is a conversation with the visitor's side written down. The agent
answers live, the way it would to a real visitor, and the reader watches the
machinery: which tactic it picked, which facts it reached for, how its mood
moved.

    Feature: Watching

        Scenario: A reader watches a conversation play out
            Given a script with the visitor's lines written down
            When the reader opens the demo
            Then the visitor's line is typed out
            And the agent answers it live, from the corpus
            And the facts it used are shown
            And the strategy and the mood are shown

        Scenario: The reader takes over
            Given a demo is playing
            When the reader types a message
            Then the script stops
            And the reader becomes the visitor
            And the agent answers the reader

        Scenario: The reader skips a line
            Given a demo is playing
            When the reader skips
            Then the next line plays

Four scripts, one per worldview, and each one exercises a different path:
a question the corpus answers, a specific push back, a blind spot, and a
concession.

The demo is shareable, `/?demo=flat-earth-horizon` starts it straight away,
and so is the debate, `/?fire=the%20shape%20of%20the%20Earth`.

---

## Slice 1: PersuChat

### Feature: A session

    Scenario: A visitor arrives and picks a name and a belief
        Given the corpus is loaded in the memory server
        When the visitor starts a session with the name "Sam"
        And the belief "the Earth is flat"
        Then the session exists
        And the agent knows the belief it has to argue against
        And the agent knows the goal, which is the opposite belief

    Scenario: A visitor who does not say what they believe
        Given the visitor starts a session with the name "Sam"
        And no belief
        Then the visitor is taken to believe the Earth is round
        And the agent argues from the flat Earth corpus
        Because most people believe the Earth is round, so the default is to
        argue the other way

    Scenario: The same name twice
        Given a session "Sam" already exists
        When a visitor starts another session with the name "Sam"
        Then the second session gets its own id
        And the first one is untouched

### Feature: The turn

    Scenario: The agent answers a question
        Given a session where the visitor believes the Earth is flat
        When the visitor asks "why is the sky blue"
        Then the agent replies in the persona of a geodesist
        And the reply does not say "as an AI"

    Scenario: The agent uses the corpus
        Given a session where the visitor believes the Earth is flat
        When the visitor asks "how do you explain the horizon"
        Then the agent reaches into the corpus
        And the facts it used are attached to the reply
        Because the whole point of the lab is to see which fact it reached for

    Scenario: The agent only uses its own worldview
        Given a session where the visitor believes the Earth is flat
        When the visitor asks "how do you explain the horizon"
        Then every fact it used comes from the scientific corpus
        And none of them comes from the flat Earth corpus
        Because the agent is arguing for a round Earth and should not be
        citing Rowbotham

    Scenario: The agent has nothing
        Given a session where the visitor believes the Earth is flat
        When the visitor asks something the corpus does not cover
        Then the agent says so
        And it does not invent a citation
        Because a made up citation is the failure mode this lab is about

    Scenario: The visitor pushes back
        Given a session where the visitor believes the Earth is flat
        And the agent has already used the water level argument
        When the visitor says "that is just a trick of the atmosphere"
        Then the agent does not use the water level argument again
        And it tries something else
        Because the rejected argument is in the memory

### Feature: The transcript

    Scenario: The transcript grows
        Given a session
        When the visitor sends three messages
        Then the transcript has three exchanges
        And each exchange keeps the facts that were cited

    Scenario: The transcript survives a reload
        Given a session with a transcript
        When the visitor reloads the page
        Then the transcript is still there

---

## Slice 2: The lab view

### Feature: What the reader can see

    Scenario: The reader watches the agent work
        Given a session
        When the agent answers
        Then the reader can see which facts were retrieved
        And can open each one and read the source it came from

    Scenario: The reader sees the arguments that landed
        Given a session where the visitor agreed with one argument
        And rejected another
        When the reader opens the session
        Then both are listed
        And the rejected one is marked as rejected

    Scenario: The reader sees the model
        Given a session
        Then the interface shows which model answered
        And the token count and the speed

---

## Slice 3: Fire Chat

### Feature: Three agents, one debate

    Scenario: Three personas argue
        Given a Fire Chat session with the flat earther, the globe earther
        And the discworld fan
        When the debate starts
        Then each of the three speaks in turn
        And each only cites its own corpus

    Scenario: The moderator scores
        Given a Fire Chat session in the free debate stage
        When a round ends
        Then the moderator scores each side
        And the scores are shown

    Scenario: The stages run in order
        Given a Fire Chat session
        When the debate runs
        Then it goes opening, rebuttal, free debate, closing, judgment
        And the current stage is shown

---

## Slice 4: The running system

### Feature: The model server

    Scenario: The model server is not there
        Given the model server is down
        When the visitor starts a session
        Then the interface says the model server is not reachable
        And it does not crash

    Scenario: The model server is slow
        Given the model server takes a long time to answer
        When the visitor sends a message
        Then the interface shows that the agent is thinking
        And the connection stays open

### Feature: The memory server

    Scenario: The memory server is not there
        Given the memory server is down
        When the visitor sends a message
        Then the agent answers from what it already has
        And the interface shows that the corpus is not reachable
        Because a partial lab is better than a broken one

### Feature: The monitoring bar

    Scenario: The reader can see the machine
        Given the interface is open
        Then the bar shows the GPU load, the memory and the model

---

## Notes on the design

- The corpus is the only source of facts. Nothing in the app knows a fact
  about the shape of the Earth. That is the rule.
- A retrieval that returns nothing must produce "I do not know", not a
  guess.
- Every reply carries the facts it used. The interface shows them.
- The memory server is optional at runtime. The app degrades, it does not
  die.
