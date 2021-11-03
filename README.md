
# Amphetype

Amphetype is an advanced typing practice program.

Features include:

* Type your favorite novel!

  One of the core ideas behind Amphetype was to not just use boring
  "stock texts" for typing practice, but to allow me to practice on
  texts that I actually want to read. So one feature is the ability to
  import whole novels (for example from [Project
  Gutenberg](https://www.gutenberg.org/)) and have Amphetype
  automatically generate bite-sized lessons from the text. For
  example, when I was learning the [Colemak](https://colemak.com/)
  keyboard layout, I typed _The Metamorphosis_ by Franz Kafka!
  
* Typing statistics.

  It provides the basic typing statistics (accuracy and WPM) across
  keys, trigrams, and words. It also tries to identify parts that
  break your flow and what impact these "viscous" combinations have on
  your typing speed overall. It also shows a graphs of progress over
  time.
  
* Generate lessons from past statistics.

  Amphetype features an advanced lesson generator where you can
  generate texts based on your past performance. Generate blocks of
  text to target practice your slowest words, trigrams, or keys!

* Layout-agnostic.

  Amphetype doesn't care _what_ keyboard or layout you use, it only
  looks at _how_ you use it.

* Highly customizable in functionality, looks, and feel.

# Installing

## GNU/Linux

Install via pip:

```bash
$ pip install --user amphetype
```

Note that Amphetype requires Python 3.6+.

## Windows

Check out the releases for an installer.

## MacOS

Here I will pretty much just copy instructions out of Google, because
I have no experience with OSX.

(If you're an experienced user, the Linux instructions above
are probably enough.)

1. First install [Homebrew](https://brew.sh/) if you don't have it.
2. Then (still in a terminal) install Python 3, also if you don't have it:
   ```bash
   $ brew install python
   ```
3. I've encountered one user who had to manually install `pyqt5`:
   ```bash
   $ brew install pyqt5
   ```
   Not sure if this is necessary, or indeed if it installs its own Python, thus
   making step #2 redundant.
4. Either way, hopefully you will now either:
   1. Have a command called `pip` (or `pip3`?), so
      use that like in the Linux instructions:
      ```bash
      $ pip install --user amphetype
      ```
   2. OR, if not, you should at least have Python
      so you could try:
      ```bash
      $ python3 -m pip install amphetype
      ```
      (The command might be `python3.9` or `python3.10` instead of `python3`.)
5. Run the program:
   ```bash
   $ amphetype
   ```
   (Might also work to find it with Finder? I don't really know! If a OSX dev is willing to write
   better and less confusing instructions, let me know!)

# Resurrected?

Yes, I originally made this program 12 years ago
[here](https://code.google.com/archive/p/amphetype/). I've updated it
somewhat and implemented some features that were requested back then,
and upgraded the code to use Python 3 and Qt5 (instead of Python 2 and
Qt4).

Google Code has gone read-only though, so I am unable to do anything
about what's shown there.

# Other Links

Review of (old) Amphetype: https://forum.colemak.com/topic/2201-training-with-amphetype/

My own inspiration for switching to a different keyboard layout and why I made Amphetype:

* http://steve-yegge.blogspot.com/2008/09/programmings-dirtiest-little-secret.html

* https://blog.codinghorror.com/we-are-typists-first-programmers-second/

* https://www.ryanheise.com/colemak/

# Screenshots

**TODO**: make actually attractive screenshots.

Using various themes:

![screenshot1](screenshot-typer.png)
![screenshot2](screenshot-pref.png)
![screenshot3](screenshot-graph.png)
![screenshot4](screenshot5.png)
