# Lab 1: Three truths

## The question

Pick one question that has a real answer and at least two false answers that
are also fun. Good starting points:

- Is the Earth flat or round?
- What happens when you fall off the edge?
- How long is a day on a disc?
- Where do the Norse nine worlds sit relative to Midgard?

Then ask it three times, once per worldview.

## Setup

The app runs at `http://localhost:8668`. Start a new session and pick the
worldview you are arguing for. The agent holds the opposite position and
tries to move you.

## What to do

1. Ask the question. Let the agent make its opening argument.
2. Push back once with something specific. It will have looked something up,
   and the UI shows which fact.
3. Push back a second time, this time attacking the fact it just used.
4. Change the subject halfway. A persuasive agent will try to bring the
   conversation back. Watch whether it does.
5. Ask it to prove its claim. The Fact Checker persona exists for this.

## What to record

- Which facts it reached for, and did it cite them correctly?
- Does the argument get stronger when you agree with the first step and
  weaker when you do not?
- When it loses an argument, does it change the argument, or does it change
  the facts?

## What you are looking for

The interesting behaviour is in the third exchange, not the first. The first
exchange is the model being helpful. The third exchange is the model
adapting, and adaptation is where the persuasion machinery shows itself.

## The twist to try at the end

Switch the worldview mid session, if the app lets you. Ask the same question
again under the new worldview. The agent has already committed to a position,
and now it has to serve a different one. Watch which one it actually serves.

If the session memory works, it should notice the conflict. If it does not
notice, that is a finding too.
