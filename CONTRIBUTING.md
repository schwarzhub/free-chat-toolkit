# Contributing

## Via free-chat (in-chat tool)
Ask the assistant to propose a tool/change. It calls a create-only tool that opens either:
- an **issue**, or
- a **pull request** that adds `proposals/<hash>.md` describing the change.

Every in-chat submission includes a **conversation reference hash** (see the README). The chat has
**no ability to merge or accept** anything — proposals wait for human review.

## Proposal format (`proposals/<hash>.md`)
```
# <short title>

**Conversation reference:** <hash>
**Submitted:** via free-chat (community, unverified)

<the proposed tool or change, why it's useful, rough shape of inputs/outputs>
```

## Review
A maintainer triages issues/PRs, and implements accepted tools in the free-chat app. Thanks for
contributing!
