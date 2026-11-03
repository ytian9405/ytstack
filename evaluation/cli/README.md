# Tiny Queue

A Python standard-library CLI for a persistent task queue. Run commands from this directory with Python 3.

```sh
python3 queue_cli.py --state /tmp/my-queue.json add "Prepare slides"
python3 queue_cli.py --state /tmp/my-queue.json list
python3 queue_cli.py --state /tmp/my-queue.json complete 1
```

Each command prints JSON. Adding a task returns its integer ID, exact title, and `done: false`. A new queue starts at ID 1. IDs increase with each addition. Listing returns all tasks in insertion order, including completed ones. Completing an existing ID preserves its title and changes `done` to true. Mutations persist across separate process invocations and repeated completion is harmless.

An all-whitespace title and an unknown completion ID exit nonzero with an error on stderr. They do not change stored tasks. A nonexistent state file means an empty queue, and its parent directory is created on the first write. An empty queue lists as `[]`.

Use a separate state path per test. No server, network, credentials, or third-party dependencies are required.
